"""Pruebas de la interfaz web: se arranca el servidor de verdad (en un puerto libre y con
una base de datos temporal) y se le hacen peticiones HTTP como lo haría el navegador."""
import http.client
import json
import re
import threading
from urllib.parse import parse_qs, quote, unquote, urlencode, urlsplit

from gestor import intercambio
from gestor.web_servidor import MAX_CUERPO, crear_servidor

from .base import BaseConBD, conexion


class BaseWeb(BaseConBD):
    def setUp(self):
        super().setUp()
        self.apagado = threading.Event()
        self.servidor = crear_servidor(puerto=0, al_apagar=self.apagado.set)
        self.puerto = self.servidor.server_address[1]
        self.host = f"127.0.0.1:{self.puerto}"
        # poll_interval pequeño: así parar el servidor al acabar cada test es instantáneo
        hilo = threading.Thread(target=self.servidor.serve_forever, args=(0.01,), daemon=True)
        hilo.start()
        # se ejecutan en orden inverso: primero se para, luego se cierra, luego se espera
        self.addCleanup(hilo.join, 5)
        self.addCleanup(self.servidor.server_close)
        self.addCleanup(self.servidor.shutdown)

    # ---------- cliente HTTP ----------

    def pedir(self, metodo, ruta, cuerpo=None, cabeceras=None, origen=True):
        h = dict(cabeceras or {})
        if metodo == "POST" and origen:
            h.setdefault("Origin", f"http://{self.host}")
        con = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=10)
        try:
            con.request(metodo, ruta, body=cuerpo, headers=h)
            r = con.getresponse()
            return r.status, {k.lower(): v for k, v in r.getheaders()}, r.read()
        finally:
            con.close()

    def get(self, ruta, **kw):
        return self.pedir("GET", ruta, **kw)

    def post(self, ruta, campos=None, **kw):
        cabeceras = {"Content-Type": "application/x-www-form-urlencoded"}
        return self.pedir("POST", ruta, urlencode(campos or {}), cabeceras, **kw)

    def html(self, ruta):
        estado, _, datos = self.get(ruta)
        self.assertEqual(estado, 200, ruta)
        return datos.decode("utf-8")

    def aviso(self, cabeceras):
        """(mensaje, tipo) que lleva una redirección en su dirección."""
        consulta = parse_qs(urlsplit(cabeceras["location"]).query)
        return consulta.get("msg", [""])[0], consulta.get("tipo", [""])[0]

    # ---------- atajos ----------

    def crear(self, termino, area="Gen", definicion="", otro=False):
        campos = {"termino": termino, "area": area, "definicion": definicion}
        if otro:
            campos["otro_significado"] = "on"
        estado, cab, datos = self.post("/concepto/nuevo", campos)
        if estado == 303:
            return int(re.search(r"/concepto/(\d+)", cab["location"]).group(1))
        return None

    def api(self, ruta, cuerpo, cabeceras=None):
        estado, _, datos = self.pedir("POST", ruta, cuerpo, cabeceras or {})
        self.assertEqual(estado, 200)
        return json.loads(datos)

    def revisar_csv(self, csv, area=""):
        cab = {"X-Area": quote(area), "Content-Type": "application/octet-stream"}
        return self.api("/api/importar/previsualizar", csv if isinstance(csv, bytes) else csv.encode("utf-8"), cab)

    def confirmar(self, token):
        return self.api("/api/importar/confirmar", json.dumps({"token": token}).encode(),
                        {"Content-Type": "application/json"})


class TestPaginas(BaseWeb):
    def test_portada_vacia(self):
        estado, cab, datos = self.get("/")
        self.assertEqual(estado, 200)
        self.assertIn("text/html", cab["content-type"])
        self.assertIn("Todavía no hay ningún término", datos.decode())

    def test_paginas_que_no_existen(self):
        self.assertEqual(self.get("/nada")[0], 404)
        self.assertEqual(self.get("/concepto/999")[0], 404)

    def test_cabeceras_de_seguridad(self):
        _, cab, _ = self.get("/")
        self.assertIn("frame-ancestors 'none'", cab["content-security-policy"])
        self.assertEqual(cab["x-content-type-options"], "nosniff")
        self.assertEqual(cab["cache-control"], "no-store")

    def test_la_pagina_de_importar_se_sirve(self):
        self.assertIn("Revisar archivo", self.html("/importar"))


class TestNuevoConcepto(BaseWeb):
    def test_crear_un_termino(self):
        id_ = self.crear("chocolate", "Comida", "Dulce")
        self.assertIsNotNone(id_)
        self.assertEqual(self.volcado(), [("Comida", "Dulce", "ES", "chocolate")])
        self.assertIn("chocolate", self.html("/"))

    def test_tras_crear_se_va_a_la_pagina_del_termino_con_un_mensaje(self):
        estado, cab, _ = self.post("/concepto/nuevo", {"termino": "casa", "area": "Hogar"})
        self.assertEqual(estado, 303)
        self.assertIn("creado", self.aviso(cab)[0])

    def test_faltan_datos_obligatorios(self):
        for campos, texto in [({"termino": "", "area": "A"}, "Escribe el término"),
                              ({"termino": "casa", "area": ""}, "Escribe el área")]:
            with self.subTest(texto=texto):
                estado, _, datos = self.post("/concepto/nuevo", campos)
                self.assertEqual(estado, 200)
                self.assertIn(texto, datos.decode())
        self.assertEqual(self.volcado(), [])

    def test_si_falla_se_conserva_lo_que_se_habia_escrito(self):
        _, _, datos = self.post("/concepto/nuevo", {"termino": "casa", "area": "", "definicion": "Vivienda"})
        pagina = datos.decode()
        self.assertIn('value="casa"', pagina)
        self.assertIn('value="Vivienda"', pagina)

    def test_tildes_y_enie_se_conservan(self):
        self.crear("Árbol", "Botánica", "Planta leñosa")
        self.crear("ñandú", "Zoología")
        pagina = self.html("/")
        for texto in ("Árbol", "Planta leñosa", "ñandú"):
            self.assertIn(texto, pagina)

    def test_lo_que_se_escribe_nunca_se_interpreta_como_html(self):
        self.crear("<script>alert(1)</script>", "<b>x</b>", '"><img src=x onerror=alert(1)>')
        pagina = self.html("/")
        self.assertNotIn("<script>alert(1)", pagina)
        self.assertNotIn("<img src=x", pagina)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", pagina)


class TestVariosSignificados(BaseWeb):
    def setUp(self):
        super().setUp()
        self.crear("banco", "Mobiliario", "Asiento largo")

    def test_repetir_el_termino_sin_marcar_la_casilla_se_rechaza_y_lista_los_significados(self):
        self.assertIsNone(self.crear("banco", "Finanzas", "Dinero"))
        _, _, datos = self.post("/concepto/nuevo", {"termino": "BANCO", "area": "Finanzas", "definicion": "Dinero"})
        pagina = datos.decode()
        self.assertIn("ya existe con estos significados", pagina)
        self.assertIn("Asiento largo", pagina)
        self.assertEqual(len(self.volcado()), 1)

    def test_otro_significado_exige_definicion(self):
        _, _, datos = self.post("/concepto/nuevo", {"termino": "banco", "area": "Finanzas",
                                                    "definicion": "", "otro_significado": "on"})
        self.assertIn("la definición es obligatoria", datos.decode())

    def test_otro_significado_con_definicion_se_crea(self):
        self.assertIsNotNone(self.crear("banco", "Finanzas", "Entidad de dinero", otro=True))
        pagina = self.html("/")
        self.assertIn("Asiento largo", pagina)
        self.assertIn("Entidad de dinero", pagina)

    def test_misma_definicion_se_rechaza(self):
        _, _, datos = self.post("/concepto/nuevo", {"termino": "banco", "area": "X",
                                                    "definicion": "ASIENTO LARGO", "otro_significado": "on"})
        self.assertIn("misma definición", datos.decode())
        self.assertEqual(len(self.volcado()), 1)


class TestBuscar(BaseWeb):
    def test_busqueda_sin_tildes_ni_mayusculas_y_por_traduccion(self):
        id_ = self.crear("Árbol", "Botánica")
        self.post(f"/concepto/{id_}/traduccion", {"idioma": "EN", "termino": "tree"})
        self.crear("casa", "Hogar")
        for consulta in ("ARBOL", "tre"):
            with self.subTest(consulta=consulta):
                pagina = self.html("/?q=" + quote(consulta))
                self.assertIn("Árbol", pagina)
                self.assertNotIn(">casa<", pagina)

    def test_sin_resultados(self):
        self.crear("casa")
        self.assertIn("No hay resultados", self.html("/?q=zzz"))


class TestEditarYBorrarConceptos(BaseWeb):
    def test_editar(self):
        id_ = self.crear("casa", "Hogar", "vieja")
        estado, cab, _ = self.post(f"/concepto/{id_}/editar",
                                   {"termino": "vivienda", "area": "Inmuebles", "definicion": "nueva"})
        self.assertEqual((estado, self.aviso(cab)), (303, ("Cambios guardados.", "ok")))
        self.assertEqual(self.volcado(), [("Inmuebles", "nueva", "ES", "vivienda")])

    def test_editar_a_algo_que_ya_existe_se_rechaza(self):
        self.crear("casa", "A", "d")
        id_ = self.crear("hogar", "A", "d")
        _, cab, _ = self.post(f"/concepto/{id_}/editar", {"termino": "CASA", "area": "A", "definicion": "d"})
        self.assertEqual(self.aviso(cab)[1], "error")
        self.assertIn("hogar", [t for _, _, i, t in self.volcado() if i == "ES"])

    def test_editar_con_campos_vacios_se_rechaza(self):
        id_ = self.crear("casa", "A")
        _, cab, _ = self.post(f"/concepto/{id_}/editar", {"termino": "", "area": "A", "definicion": ""})
        self.assertEqual(self.aviso(cab)[1], "error")
        self.assertEqual(self.volcado(), [("A", "", "ES", "casa")])

    def test_borrar_borra_tambien_las_traducciones(self):
        id_ = self.crear("casa")
        self.post(f"/concepto/{id_}/traduccion", {"idioma": "EN", "termino": "house"})
        estado, cab, _ = self.post(f"/concepto/{id_}/borrar")
        self.assertEqual(estado, 303)
        self.assertEqual(self.volcado(), [])

    def test_operar_sobre_algo_que_ya_no_existe(self):
        for ruta in ("/concepto/999/editar", "/concepto/999/borrar", "/concepto/999/traduccion",
                     "/traduccion/999/editar", "/traduccion/999/borrar"):
            with self.subTest(ruta=ruta):
                estado, cab, _ = self.post(ruta, {"termino": "x", "area": "x", "idioma": "EN"})
                self.assertEqual((estado, self.aviso(cab)[1]), (303, "error"))


class TestTraducciones(BaseWeb):
    def setUp(self):
        super().setUp()
        self.id = self.crear("casa", "Hogar")

    def anadir(self, idioma, termino):
        _, cab, _ = self.post(f"/concepto/{self.id}/traduccion", {"idioma": idioma, "termino": termino})
        return self.aviso(cab)

    def traducciones(self):
        return [(i, t) for _, _, i, t in self.volcado() if i != "ES"]

    def test_anadir_varias(self):
        self.assertEqual(self.anadir("en", "house")[1], "ok")
        self.anadir("EN", "home")
        self.anadir("FR", "maison")
        self.assertEqual(self.traducciones(), [("EN", "home"), ("EN", "house"), ("FR", "maison")])

    def test_rechazos(self):
        self.anadir("EN", "house")
        for idioma, termino, texto in [("ES", "x", "origen"), ("x", "x", "2 o 3 letras"),
                                       ("EN", "house", "ya existe"), ("EN", "", "vacía")]:
            with self.subTest(idioma=idioma, termino=termino):
                mensaje, tipo = self.anadir(idioma, termino)
                self.assertEqual(tipo, "error")
                self.assertIn(texto, mensaje)
        self.assertEqual(self.traducciones(), [("EN", "house")])

    def id_termino(self, idioma, termino):
        with conexion() as conn:
            return conn.execute("SELECT id_termino FROM Terminos WHERE idioma = ? AND termino = ?",
                                (idioma, termino)).fetchone()[0]

    def test_editar(self):
        self.anadir("EN", "house")
        _, cab, _ = self.post(f"/traduccion/{self.id_termino('EN', 'house')}/editar",
                              {"idioma": "de", "termino": "Haus"})
        self.assertEqual(self.aviso(cab)[1], "ok")
        self.assertEqual(self.traducciones(), [("DE", "Haus")])

    def test_editar_a_una_que_ya_existe(self):
        self.anadir("EN", "house")
        self.anadir("EN", "home")
        _, cab, _ = self.post(f"/traduccion/{self.id_termino('EN', 'home')}/editar",
                              {"idioma": "EN", "termino": "house"})
        self.assertEqual(self.aviso(cab)[1], "error")
        self.assertEqual(self.traducciones(), [("EN", "home"), ("EN", "house")])

    def test_borrar(self):
        self.anadir("EN", "house")
        self.post(f"/traduccion/{self.id_termino('EN', 'house')}/borrar")
        self.assertEqual(self.traducciones(), [])

    def test_la_pagina_del_termino_muestra_sus_traducciones_y_el_mensaje(self):
        self.anadir("EN", "house")
        _, cab, _ = self.post(f"/concepto/{self.id}/traduccion", {"idioma": "FR", "termino": "maison"})
        pagina = self.html(cab["location"])
        self.assertIn("Traducción añadida.", pagina)
        self.assertIn('value="house"', pagina)
        self.assertIn('value="maison"', pagina)


class TestExportarPorWeb(BaseWeb):
    def test_sin_datos_vuelve_a_la_portada_con_un_aviso(self):
        estado, cab, _ = self.get("/exportar")
        self.assertEqual(estado, 303)
        self.assertEqual(self.aviso(cab)[1], "error")

    def test_descarga_un_csv_listo_para_excel(self):
        id_ = self.crear("casa", "Hogar", "Vivienda")
        self.post(f"/concepto/{id_}/traduccion", {"idioma": "EN", "termino": "house"})
        estado, cab, datos = self.get("/exportar")
        self.assertEqual(estado, 200)
        self.assertIn("text/csv", cab["content-type"])
        self.assertIn("attachment", cab["content-disposition"])
        self.assertRegex(cab["content-disposition"], r'glosario_\d{4}-\d{2}-\d{2}\.csv')
        self.assertTrue(datos.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(datos.decode("utf-8-sig").splitlines(),
                         ["Área;Definición;ES;EN", "Hogar;Vivienda;casa;house"])


class TestImportarPorWeb(BaseWeb):
    CSV = "Área;Definición;ES;EN\nHogar;Vivienda;casa;house\nComida;;tarta;cake\n"

    def test_revisar_no_guarda_nada(self):
        r = self.revisar_csv(self.CSV)
        self.assertTrue(r["ok"] and r["hay_cambios"] and r["token"])
        self.assertIn("2 concepto(s) nuevo(s)", r["lineas"])
        self.assertEqual(self.volcado(), [])

    def test_confirmar_guarda(self):
        token = self.revisar_csv(self.CSV)["token"]
        r = self.confirmar(token)
        self.assertTrue(r["ok"])
        self.assertIn("2 concepto(s) nuevo(s)", r["mensaje"])
        self.assertIn(("Hogar", "Vivienda", "EN", "house"), self.volcado())

    def test_una_revision_solo_se_puede_confirmar_una_vez(self):
        token = self.revisar_csv(self.CSV)["token"]
        self.confirmar(token)
        r = self.confirmar(token)
        self.assertFalse(r["ok"])
        self.assertIn("caducado", r["error"])
        self.assertEqual(len(self.volcado()), 4)

    def test_token_inventado_o_cuerpo_roto(self):
        self.assertFalse(self.confirmar("inventado")["ok"])
        r = self.api("/api/importar/confirmar", b"esto no es json", {"Content-Type": "application/json"})
        self.assertFalse(r["ok"])

    def test_archivo_mal_formado_o_vacio(self):
        self.assertIn("columna 'ES'", self.revisar_csv("Área;EN\nA;b\n")["error"])
        self.assertFalse(self.revisar_csv(b"")["ok"])

    def test_nada_nuevo(self):
        self.confirmar(self.revisar_csv(self.CSV)["token"])
        r = self.revisar_csv(self.CSV)
        self.assertEqual((r["ok"], r["hay_cambios"]), (True, False))

    def test_area_por_defecto_con_tildes(self):
        self.confirmar(self.revisar_csv("ES;EN\ncasa;house\n", area="Hogar áé")["token"])
        self.assertIn(("Hogar áé", "", "ES", "casa"), self.volcado())

    def test_codificacion_antigua_de_excel(self):
        r = self.revisar_csv("Área;ES\nZoología;ñandú\n".encode("cp1252"))
        self.assertTrue(r["ok"])
        self.assertIn("Windows-1252", r["lineas"][0])

    def test_errores_y_avisos_con_su_numero_de_fila(self):
        r = self.revisar_csv("Área;ES\nA;ok\n;sin area\n")
        self.assertEqual(r["errores"], ["fila 3: falta el área"])

    def test_ida_y_vuelta_exportar_e_importar_por_web(self):
        id_ = self.crear("banco", "Mobiliario", "Asiento")
        self.post(f"/concepto/{id_}/traduccion", {"idioma": "EN", "termino": "bench"})
        self.crear("banco", "Finanzas", "Dinero", otro=True)
        original = self.volcado()
        _, _, csv = self.get("/exportar")
        with conexion() as conn:
            conn.execute("DELETE FROM Conceptos")
        self.confirmar(self.revisar_csv(csv)["token"])
        self.assertEqual(self.volcado(), original)


class TestSeguridad(BaseWeb):
    def test_un_nombre_de_host_falso_se_rechaza(self):
        self.assertEqual(self.get("/", cabeceras={"Host": "malo.example"})[0], 403)
        self.assertEqual(self.get("/", cabeceras={"Host": "127.0.0.1:1"})[0], 403)

    def test_localhost_tambien_vale(self):
        self.assertEqual(self.get("/", cabeceras={"Host": f"localhost:{self.puerto}"})[0], 200)

    def test_un_formulario_enviado_desde_otra_web_se_rechaza(self):
        for origen in ("http://malo.example", "https://127.0.0.1:%d" % self.puerto, "http://127.0.0.1:1"):
            with self.subTest(origen=origen):
                estado, _, _ = self.pedir(
                    "POST", "/concepto/nuevo", urlencode({"termino": "x", "area": "y"}),
                    {"Origin": origen, "Content-Type": "application/x-www-form-urlencoded"}, origen=False)
                self.assertEqual(estado, 403)
        self.assertEqual(self.volcado(), [])

    def test_sec_fetch_site_de_otro_sitio_se_rechaza(self):
        estado, _, _ = self.pedir("POST", "/concepto/nuevo", "termino=x&area=y",
                                  {"Sec-Fetch-Site": "cross-site",
                                   "Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(estado, 403)
        self.assertEqual(self.volcado(), [])

    def test_las_peticiones_sin_origen_no_vienen_de_un_navegador_y_se_aceptan(self):
        estado, _, _ = self.post("/concepto/nuevo", {"termino": "x", "area": "y"}, origen=False)
        self.assertEqual(estado, 303)

    def test_cerrar_solo_funciona_con_post(self):
        self.assertEqual(self.get("/apagar")[0], 404)
        self.assertFalse(self.apagado.is_set())

    def test_cerrar_programa(self):
        estado, _, datos = self.post("/apagar")
        self.assertEqual(estado, 200)
        self.assertIn("Programa cerrado", datos.decode())
        self.assertTrue(self.apagado.wait(3))

    def _con_cabecera_de_longitud(self, valor):
        con = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=10)
        try:
            con.putrequest("POST", "/api/importar/previsualizar")
            con.putheader("Origin", f"http://{self.host}")
            con.putheader("Content-Length", valor)
            con.endheaders()
            return con.getresponse().status
        finally:
            con.close()

    def test_cuerpo_demasiado_grande(self):
        self.assertEqual(self._con_cabecera_de_longitud(str(MAX_CUERPO + 1)), 413)

    def test_longitud_no_valida(self):
        self.assertEqual(self._con_cabecera_de_longitud("abc"), 400)
        self.assertEqual(self._con_cabecera_de_longitud("-5"), 400)

    def test_un_error_interno_no_tumba_el_servidor(self):
        from unittest import mock
        with mock.patch("gestor.web_servidor.repo.listar_conceptos", side_effect=RuntimeError("boom")), \
                mock.patch("traceback.print_exc"):
            self.assertEqual(self.get("/")[0], 500)
        self.assertEqual(self.get("/")[0], 200)


if __name__ == "__main__":
    import unittest
    unittest.main()