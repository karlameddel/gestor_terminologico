"""Servidor web local: la interfaz del gestor en el navegador.

Solo usa la biblioteca estándar de Python (nada que instalar). Escucha únicamente
en 127.0.0.1, es decir, solo se puede abrir desde este mismo ordenador.

Como el resto de capas, aquí no se imprime nada por pantalla ni se abre el
navegador: de eso se encarga app_web.py. La lógica del diccionario es la de
repositorio.py e intercambio.py; este módulo solo traduce peticiones web a esas
llamadas y las respuestas a HTML (web_vistas.py).
"""
import json
import re
import secrets
import sqlite3
import sys
import threading
import traceback
from collections import OrderedDict, namedtuple
from contextlib import closing
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlencode, urlsplit

from . import intercambio, repositorio as repo, web_vistas as vistas
from .basedatos import conectar

MAX_CUERPO = 20 * 1024 * 1024        # 20 MB: más que de sobra para un glosario
MAX_REVISIONES_PENDIENTES = 5

Respuesta = namedtuple("Respuesta", "estado cabeceras cuerpo")


def _html(texto, estado=200):
    return Respuesta(estado, {"Content-Type": "text/html; charset=utf-8"}, texto.encode("utf-8"))


def _json(objeto, estado=200):
    return Respuesta(estado, {"Content-Type": "application/json; charset=utf-8"},
                     json.dumps(objeto, ensure_ascii=False).encode("utf-8"))


def _redirigir(ruta, mensaje="", tipo="ok"):
    """303: el navegador pasa a pedir `ruta` con un GET (así F5 no repite el envío)."""
    if mensaje:
        ruta += ("&" if "?" in ruta else "?") + urlencode({"msg": mensaje, "tipo": tipo})
    return Respuesta(303, {"Location": ruta}, b"")


def _error_pagina(estado, texto):
    return _html(vistas.vista_error(estado, texto), estado)


def _formulario(cuerpo):
    datos = parse_qs(cuerpo.decode("utf-8", errors="replace"), keep_blank_values=True)
    return {clave: valores[0].strip() for clave, valores in datos.items()}


def _lineas_resumen(res):
    sep = "tabulador" if res.separador == "\t" else f"'{res.separador}'"
    lineas = [f"{res.filas_leidas} fila(s) leída(s) · separador {sep} · codificación {res.codificacion}",
              "Idiomas detectados: " + ", ".join(["ES"] + res.idiomas)]
    if res.columnas_ignoradas:
        lineas.append("Columnas ignoradas: " + ", ".join(res.columnas_ignoradas))
    lineas += [f"{res.conceptos_nuevos} concepto(s) nuevo(s)",
               f"{res.conceptos_ampliados} concepto(s) existente(s) ampliado(s) con traducciones",
               f"{res.traducciones_nuevas} traducción(es) añadida(s) en total",
               f"{res.sin_cambios} fila(s) que ya estaban en el diccionario"]
    return lineas


def _recortar(lineas, maximo=30):
    if len(lineas) > maximo:
        return lineas[:maximo] + [f"... y {len(lineas) - maximo} más"]
    return lineas


class Aplicacion:
    """Las rutas de la web y lo que hace cada una."""

    def __init__(self, al_apagar=None):
        self.al_apagar = al_apagar
        self.hosts_permitidos = set()
        self._pendientes = OrderedDict()       # revisiones de CSV a la espera de confirmar
        self._cerrojo = threading.Lock()

    # ---------- Seguridad ----------

    def host_permitido(self, host):
        """Evita ataques de 'DNS rebinding': solo se atiende si se pidió a localhost."""
        return (host or "").lower() in self.hosts_permitidos

    def origen_permitido(self, cabeceras):
        """Evita que OTRA página web abierta en tu navegador envíe formularios a este
        programa. Las peticiones sin Origin (curl, tests) no vienen de un navegador."""
        if cabeceras.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
            return False
        origen = cabeceras.get("Origin")
        if not origen:
            return True
        partes = urlsplit(origen)
        return partes.scheme == "http" and partes.netloc.lower() in self.hosts_permitidos

    # ---------- Reparto de rutas ----------

    def manejar(self, metodo, ruta, params, cuerpo, cabeceras):
        tabla = self._RUTAS_GET if metodo == "GET" else self._RUTAS_POST
        for patron, nombre in tabla:
            m = patron.match(ruta)
            if m:
                ids = [int(x) for x in m.groups()]
                return getattr(self, nombre)(*ids, params=params, cuerpo=cuerpo, cabeceras=cabeceras)
        return _error_pagina(404, "No existe esa página")

    # ---------- Páginas (GET) ----------

    @staticmethod
    def _aviso(params):
        mensaje = params.get("msg", [""])[0][:300]
        tipo = "error" if params.get("tipo", [""])[0] == "error" else "ok"
        return mensaje, tipo

    def _datos_indice(self, conn, consulta):
        filas = repo.buscar_conceptos(conn, consulta) if consulta else repo.listar_conceptos(conn)
        conceptos = []
        for c in filas:
            por_idioma = {}
            for t in repo.obtener_traducciones(conn, c["id_concepto"]):
                por_idioma.setdefault(t["idioma"], []).append(t["termino"])
            conceptos.append({"id": c["id_concepto"], "termino": c["termino_es"], "area": c["area"],
                              "definicion": c["definicion"], "traducciones": list(por_idioma.items())})
        return conceptos

    def _indice(self, *, params, **_):
        consulta = params.get("q", [""])[0].strip()
        mensaje, tipo = self._aviso(params)
        with closing(conectar()) as conn:
            conceptos = self._datos_indice(conn, consulta)
        return _html(vistas.vista_indice(conceptos, consulta, mensaje=mensaje, tipo=tipo))

    def _indice_con_error(self, error, valores):
        """Vuelve a mostrar el formulario con lo que la persona había escrito."""
        with closing(conectar()) as conn:
            conceptos = self._datos_indice(conn, "")
        return _html(vistas.vista_indice(conceptos, valores=valores, abrir_formulario=True,
                                         mensaje=error, tipo="error"))

    def _ver_concepto(self, id_concepto, *, params, **_):
        mensaje, tipo = self._aviso(params)
        with closing(conectar()) as conn:
            c = repo.concepto_por_id(conn, id_concepto)
            traducciones = repo.obtener_traducciones(conn, id_concepto) if c else []
        if c is None:
            return _error_pagina(404, "Ese término no existe (puede que lo hayas borrado)")
        return _html(vistas.vista_concepto(c, traducciones, mensaje, tipo))

    def _ver_importar(self, **_):
        return _html(vistas.vista_importar())

    def _exportar(self, **_):
        with closing(conectar()) as conn:
            datos, n, _idiomas = intercambio.exportar_bytes(conn)
        if n == 0:
            return _redirigir("/", "No hay términos que exportar todavía.", "error")
        nombre = f"glosario_{date.today():%Y-%m-%d}.csv"
        return Respuesta(200, {"Content-Type": "text/csv; charset=utf-8",
                               "Content-Disposition": f'attachment; filename="{nombre}"'}, datos)

    # ---------- Acciones (POST) sobre conceptos ----------

    def _nuevo_concepto(self, *, cuerpo, **_):
        f = _formulario(cuerpo)
        termino, area, definicion = f.get("termino", ""), f.get("area", ""), f.get("definicion", "")
        otro_significado = "otro_significado" in f
        error, id_nuevo = None, None
        with closing(conectar()) as conn, conn:
            existentes = repo.conceptos_por_termino_es(conn, termino) if termino else []
            if not termino:
                error = "Escribe el término en español."
            elif not area:
                error = "Escribe el área."
            elif existentes and not otro_significado:
                lista = "; ".join(f"[{c['area']}] {c['definicion'] or 'sin definición'}"
                                  for c in existentes)
                error = (f"«{termino}» ya existe con estos significados: {lista}. "
                         "Si es un significado distinto, marca la casilla y escribe su definición.")
            elif existentes and not definicion:
                error = "Para añadir otro significado, la definición es obligatoria."
            elif repo.hay_significado_repetido(conn, termino, definicion):
                error = "Ya existe ese término con esa misma definición."
            else:
                id_nuevo = repo.crear_concepto(conn, area, termino, definicion)
        if error:
            return self._indice_con_error(error, f)
        return _redirigir(f"/concepto/{id_nuevo}",
                          f"Término «{termino}» creado. Ahora puedes añadir sus traducciones.")

    def _editar_concepto(self, id_concepto, *, cuerpo, **_):
        f = _formulario(cuerpo)
        termino, area, definicion = f.get("termino", ""), f.get("area", ""), f.get("definicion", "")
        with closing(conectar()) as conn, conn:
            if repo.concepto_por_id(conn, id_concepto) is None:
                return _redirigir("/", "Ese término ya no existe.", "error")
            if not termino or not area:
                mensaje, tipo = "El término y el área no pueden estar vacíos.", "error"
            elif repo.hay_significado_repetido(conn, termino, definicion, id_concepto):
                mensaje, tipo = "Ya existe otro concepto con ese término y esa definición.", "error"
            else:
                repo.actualizar_concepto(conn, id_concepto, area, termino, definicion)
                mensaje, tipo = "Cambios guardados.", "ok"
        return _redirigir(f"/concepto/{id_concepto}", mensaje, tipo)

    def _borrar_concepto(self, id_concepto, **_):
        with closing(conectar()) as conn, conn:
            c = repo.concepto_por_id(conn, id_concepto)
            if c is None:
                return _redirigir("/", "Ese término ya no existe.", "error")
            repo.borrar_concepto(conn, id_concepto)      # sus traducciones se borran solas
        return _redirigir("/", f"Término «{c['termino_es']}» borrado.")

    # ---------- Acciones (POST) sobre traducciones ----------

    def _anadir_traduccion(self, id_concepto, *, cuerpo, **_):
        f = _formulario(cuerpo)
        with closing(conectar()) as conn, conn:
            if repo.concepto_por_id(conn, id_concepto) is None:
                return _redirigir("/", "Ese término ya no existe.", "error")
            mensaje, tipo = self._guardar_traduccion(
                lambda: repo.crear_traduccion(conn, id_concepto, f.get("idioma", ""), f.get("termino", "")),
                f.get("termino", ""), "Traducción añadida.")
        return _redirigir(f"/concepto/{id_concepto}", mensaje, tipo)

    def _editar_traduccion(self, id_termino, *, cuerpo, **_):
        f = _formulario(cuerpo)
        with closing(conectar()) as conn, conn:
            id_concepto = repo.concepto_de_traduccion(conn, id_termino)
            if id_concepto is None:
                return _redirigir("/", "Esa traducción ya no existe.", "error")
            mensaje, tipo = self._guardar_traduccion(
                lambda: repo.actualizar_traduccion(conn, id_termino, f.get("idioma", ""), f.get("termino", "")),
                f.get("termino", ""), "Traducción actualizada.")
        return _redirigir(f"/concepto/{id_concepto}", mensaje, tipo)

    def _borrar_traduccion(self, id_termino, **_):
        with closing(conectar()) as conn, conn:
            id_concepto = repo.concepto_de_traduccion(conn, id_termino)
            if id_concepto is None:
                return _redirigir("/", "Esa traducción ya no existe.", "error")
            repo.borrar_traduccion(conn, id_termino)
        return _redirigir(f"/concepto/{id_concepto}", "Traducción borrada.")

    @staticmethod
    def _guardar_traduccion(operacion, texto, mensaje_ok):
        if not texto:
            return "La traducción no puede estar vacía.", "error"
        try:
            operacion()
        except ValueError as e:                  # código de idioma no válido
            return str(e), "error"
        except sqlite3.IntegrityError:
            return "Esa traducción ya existe para este término.", "error"
        return mensaje_ok, "ok"

    # ---------- Importar (API que usa la página con JavaScript) ----------

    def _previsualizar(self, *, cuerpo, cabeceras, **_):
        """Lee el CSV y cuenta qué pasaría, SIN guardar nada (al cerrar la conexión
        sin commit, SQLite descarta todo)."""
        area = unquote(cabeceras.get("X-Area", "")).strip()
        if not cuerpo:
            return _json({"ok": False, "error": "El archivo está vacío."})
        try:
            with closing(conectar()) as conn:
                res = intercambio.importar_bytes(conn, cuerpo, area)
        except intercambio.ErrorCSV as e:
            return _json({"ok": False, "error": str(e)})
        token = secrets.token_urlsafe(16)
        with self._cerrojo:
            self._pendientes[token] = (cuerpo, area)
            while len(self._pendientes) > MAX_REVISIONES_PENDIENTES:
                self._pendientes.popitem(last=False)
        return _json({"ok": True, "token": token, "hay_cambios": res.hay_cambios,
                      "lineas": _lineas_resumen(res),
                      "avisos": _recortar([f"fila {n}: {m}" for n, m in res.avisos]),
                      "errores": _recortar([f"fila {n}: {m}" for n, m in res.errores])})

    def _confirmar(self, *, cuerpo, **_):
        try:
            token = json.loads(cuerpo.decode("utf-8")).get("token", "")
        except (ValueError, AttributeError):
            token = ""
        with self._cerrojo:
            pendiente = self._pendientes.pop(token, None)
        if pendiente is None:
            return _json({"ok": False, "error": "La revisión ha caducado. Vuelve a revisar el archivo."})
        try:
            with closing(conectar()) as conn:
                res = intercambio.importar_bytes(conn, *pendiente)
                if res.hay_cambios:
                    conn.commit()
        except intercambio.ErrorCSV as e:
            return _json({"ok": False, "error": str(e)})
        return _json({"ok": True, "mensaje": (
            f"Importación guardada: {res.conceptos_nuevos} concepto(s) nuevo(s), "
            f"{res.conceptos_ampliados} ampliado(s), {res.traducciones_nuevas} traducción(es) añadida(s).")})

    # ---------- Cerrar ----------

    def _apagar(self, **_):
        if self.al_apagar:
            # En otro hilo: así esta respuesta llega al navegador antes de parar el servidor.
            threading.Thread(target=self.al_apagar, daemon=True).start()
        return _html(vistas.vista_apagado())

    _RUTAS_GET = [(re.compile(p), n) for p, n in [
        (r"^/$", "_indice"),
        (r"^/concepto/(\d+)$", "_ver_concepto"),
        (r"^/importar$", "_ver_importar"),
        (r"^/exportar$", "_exportar"),
    ]]
    _RUTAS_POST = [(re.compile(p), n) for p, n in [
        (r"^/concepto/nuevo$", "_nuevo_concepto"),
        (r"^/concepto/(\d+)/editar$", "_editar_concepto"),
        (r"^/concepto/(\d+)/borrar$", "_borrar_concepto"),
        (r"^/concepto/(\d+)/traduccion$", "_anadir_traduccion"),
        (r"^/traduccion/(\d+)/editar$", "_editar_traduccion"),
        (r"^/traduccion/(\d+)/borrar$", "_borrar_traduccion"),
        (r"^/api/importar/previsualizar$", "_previsualizar"),
        (r"^/api/importar/confirmar$", "_confirmar"),
        (r"^/apagar$", "_apagar"),
    ]]


class _Manejador(BaseHTTPRequestHandler):
    def log_message(self, formato, *args):      # sin ruido en la consola
        pass

    def do_GET(self):
        self._atender("GET")

    def do_POST(self):
        self._atender("POST")

    def _atender(self, metodo):
        app = self.server.app
        try:
            if not app.host_permitido(self.headers.get("Host")):
                return self._enviar(_error_pagina(403, "Acceso no permitido"))
            partes = urlsplit(self.path)
            cuerpo = b""
            if metodo == "POST":
                if not app.origen_permitido(self.headers):
                    return self._enviar(_error_pagina(403, "Petición rechazada (origen no permitido)"))
                try:
                    longitud = int(self.headers.get("Content-Length") or 0)
                except ValueError:
                    return self._enviar(_error_pagina(400, "Petición no válida"))
                if longitud < 0:
                    return self._enviar(_error_pagina(400, "Petición no válida"))
                if longitud > MAX_CUERPO:
                    return self._enviar(_error_pagina(413, "El archivo es demasiado grande (máximo 20 MB)"))
                cuerpo = self.rfile.read(longitud)
            params = parse_qs(partes.query, keep_blank_values=True)
            try:
                respuesta = app.manejar(metodo, partes.path, params, cuerpo, self.headers)
            except Exception:
                traceback.print_exc(file=sys.stderr)
                respuesta = _error_pagina(500, "Ha ocurrido un error inesperado")
            self._enviar(respuesta)
        except (BrokenPipeError, ConnectionResetError):
            pass                                  # el navegador cerró la conexión antes de tiempo

    def _enviar(self, r):
        self.send_response(r.estado)
        for clave, valor in r.cabeceras.items():
            self.send_header(clave, valor)
        self.send_header("Content-Length", str(len(r.cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; style-src 'unsafe-inline'; "
                         "script-src 'unsafe-inline'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(r.cuerpo)


class _Servidor(ThreadingHTTPServer):
    daemon_threads = True
    # En Windows, SO_REUSEADDR deja que DOS programas escuchen en el mismo puerto sin
    # error. Se desactiva ahí para que una segunda copia del gestor use otro puerto.
    allow_reuse_address = sys.platform != "win32"


def crear_servidor(host="127.0.0.1", puerto=0, al_apagar=None):
    """Crea (sin arrancar) el servidor. puerto=0 elige uno libre.
    `al_apagar` se llama cuando se pulsa «Cerrar programa»; por defecto, para el servidor."""
    servidor = _Servidor((host, puerto), _Manejador)
    app = Aplicacion(al_apagar=al_apagar or servidor.shutdown)
    puerto_real = servidor.server_address[1]
    app.hosts_permitidos = {f"127.0.0.1:{puerto_real}", f"localhost:{puerto_real}"}
    servidor.app = app
    return servidor