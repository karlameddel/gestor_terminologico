"""Importar y exportar glosarios en CSV, para abrirlos en Excel o Google Sheets.

Formato: una fila por concepto y una columna por idioma.

    Área;Definición;ES;EN;FR
    Informática;Componente principal;placa base;motherboard | mainboard;carte mère

* Varias traducciones en una misma celda se separan con " | ".
  (Por eso un término no puede contener el carácter "|".)
* Al EXPORTAR se usa ';' y UTF-8 con BOM: es lo que necesita el Excel en
  español para separar bien las columnas y mostrar tildes y ñ.
* Al IMPORTAR se detecta solo el separador (';', ',' o tabulador) y la
  codificación (UTF-8, o la antigua de Windows), así que vale tanto un CSV
  de Excel como uno descargado de Google Sheets.

Igual que repositorio.py, aquí no hay input() ni print(). Además,
importar_csv() NO hace commit: quien la llama decide si guarda
(conn.commit()) o descarta (conn.rollback()) después de enseñar el resumen.
"""
import csv
import io
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from . import repositorio as repo
from .config import IDIOMA_ORIGEN
from .texto import fold, norm

SEPARADOR_TRADUCCIONES = "|"

# Nombres de columna aceptados (se comparan sin tildes ni mayúsculas).
_ALIAS_AREA = {"area", "categoria"}
_ALIAS_DEFINICION = {"definicion"}
_ALIAS_ES = {"es", "espanol"}


class ErrorCSV(Exception):
    """El archivo no se puede importar (no existe, cabecera incorrecta...)."""


@dataclass
class ResultadoImportacion:
    filas_leidas: int = 0
    conceptos_nuevos: int = 0
    conceptos_ampliados: int = 0    # existentes a los que se añadieron traducciones
    traducciones_nuevas: int = 0    # en total (incluye las de conceptos nuevos)
    sin_cambios: int = 0            # filas que ya estaban completas
    errores: list = field(default_factory=list)   # [(nº de línea, mensaje)]
    avisos: list = field(default_factory=list)    # [(nº de línea, mensaje)]
    idiomas: list = field(default_factory=list)
    columnas_ignoradas: list = field(default_factory=list)
    separador: str = ";"
    codificacion: str = "UTF-8"
    _creados: set = field(default_factory=set, repr=False)   # ids creados en esta importación

    @property
    def hay_cambios(self):
        return bool(self.conceptos_nuevos or self.traducciones_nuevas)


# ---------- Exportar ----------

def exportar_csv(conn, ruta):
    """Escribe todo el diccionario en `ruta`.
    Devuelve (nº de conceptos, idiomas exportados). Si no hay nada, no crea el archivo."""
    conceptos = repo.listar_conceptos(conn)
    if not conceptos:
        return 0, []

    por_concepto = defaultdict(lambda: defaultdict(list))
    for t in conn.execute(
        "SELECT id_concepto, idioma, termino FROM Terminos "
        "WHERE idioma <> ? ORDER BY idioma, termino", (IDIOMA_ORIGEN,)
    ):
        por_concepto[t["id_concepto"]][t["idioma"]].append(t["termino"])
    idiomas = sorted({i for d in por_concepto.values() for i in d})

    ruta = Path(ruta)
    temporal = ruta.with_name(ruta.name + ".tmp")
    union = f" {SEPARADOR_TRADUCCIONES} "
    try:
        # Se escribe en un archivo temporal y luego se renombra: si algo falla
        # a mitad, no se estropea un archivo anterior con el mismo nombre.
        with open(temporal, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["Área", "Definición", IDIOMA_ORIGEN, *idiomas])
            for c in conceptos:
                trads = por_concepto[c["id_concepto"]]
                w.writerow([c["area"], c["definicion"], c["termino_es"],
                            *[union.join(trads[i]) for i in idiomas]])
        temporal.replace(ruta)
    finally:
        if temporal.exists():
            temporal.unlink()
    return len(conceptos), idiomas


# ---------- Importar ----------

def _leer_texto(ruta):
    try:
        datos = Path(ruta).read_bytes()
    except OSError as e:
        raise ErrorCSV(f"No se puede leer el archivo: {e.strerror or e}") from e
    try:
        return datos.decode("utf-8-sig"), "UTF-8"
    except UnicodeDecodeError:
        # "CSV (delimitado por comas)" del Excel antiguo usa la codificación de Windows.
        return datos.decode("cp1252", errors="replace"), "Windows-1252"


def _leer_filas(texto):
    """Devuelve (filas, separador, líneas descartadas al principio)."""
    lineas = texto.splitlines(keepends=True)
    descartadas = 0
    # Líneas en blanco iniciales y la línea "sep=;" que algunos programas añaden.
    while lineas and (not lineas[0].strip() or lineas[0].strip().lower().startswith("sep=")):
        lineas.pop(0)
        descartadas += 1
    if not lineas:
        raise ErrorCSV("El archivo está vacío.")

    separador = max(";,\t", key=lineas[0].count)   # el que más aparece en la cabecera
    try:
        filas = list(csv.reader(io.StringIO("".join(lineas), newline=""), delimiter=separador))
    except csv.Error as e:
        raise ErrorCSV(f"El archivo no tiene un formato CSV válido: {e}") from e
    return filas, separador, descartadas


def _interpretar_cabecera(cabecera):
    """Devuelve ({'area','definicion','es': índice o None}, {idioma: índice}, [columnas ignoradas])."""
    cols = {"area": None, "definicion": None, "es": None}
    idiomas, ignoradas = {}, []

    def repetida(nombre):
        raise ErrorCSV(f"La columna '{nombre}' aparece repetida en la cabecera.")

    for i, nombre in enumerate(cabecera):
        limpio = nombre.strip()
        if not limpio:
            continue
        clave = norm(limpio)
        if clave in _ALIAS_AREA:
            tipo = "area"
        elif clave in _ALIAS_DEFINICION:
            tipo = "definicion"
        elif clave in _ALIAS_ES:
            tipo = "es"
        elif repo.validar_idioma(limpio.upper()) is None:   # código de 2-3 letras (EN, FR...)
            if limpio.upper() in idiomas:
                repetida(limpio)
            idiomas[limpio.upper()] = i
            continue
        else:
            ignoradas.append(limpio)
            continue
        if cols[tipo] is not None:
            repetida(limpio)
        cols[tipo] = i

    if cols["es"] is None:
        raise ErrorCSV("Falta la columna 'ES' (el término en español) en la cabecera.")
    return cols, idiomas, ignoradas


def _celda(fila, indice):
    if indice is None or indice >= len(fila):
        return ""
    return fila[indice].strip()


def _importar_fila(conn, fila, cols, idiomas, area_defecto, linea, res):
    """Importa una fila. Devuelve un mensaje de error, o None si todo fue bien."""
    termino = _celda(fila, cols["es"])
    if not termino:
        return "falta el término en español"
    area = _celda(fila, cols["area"]) or area_defecto
    definicion = _celda(fila, cols["definicion"])

    traducciones = []
    for idioma, i in idiomas.items():
        for parte in _celda(fila, i).split(SEPARADOR_TRADUCCIONES):
            if parte.strip():
                traducciones.append((idioma, parte.strip()))

    # ¿A qué concepto se refiere la fila? La definición distingue los significados.
    existentes = repo.conceptos_por_termino_es(conn, termino)
    mismos = [c for c in existentes if fold(c["definicion"]) == fold(definicion)]
    id_concepto, es_nuevo = None, False
    if mismos:
        id_concepto = mismos[0]["id_concepto"]
    elif not definicion and len(existentes) == 1:
        id_concepto = existentes[0]["id_concepto"]      # sin definición: se añade al único que hay
    elif not definicion and len(existentes) > 1:
        return (f"'{termino}' tiene varios significados y la fila no indica cuál "
                "(rellena la definición)")
    else:
        if not area:
            return "falta el área"
        id_concepto = repo.crear_concepto(conn, area, termino, definicion)
        es_nuevo = True
        res._creados.add(id_concepto)
        # Solo se avisa si el otro significado ya estaba ANTES de importar; si viene
        # en el mismo archivo (dos filas de "banco"), es lo que se pretendía.
        if any(c["id_concepto"] not in res._creados for c in existentes):
            res.avisos.append((linea, f"'{termino}' ya existía con otro significado: "
                                      "se ha creado uno nuevo"))

    añadidas = 0
    for idioma, trad in traducciones:
        try:
            repo.crear_traduccion(conn, id_concepto, idioma, trad)
            añadidas += 1
        except sqlite3.IntegrityError:
            pass    # esa traducción ya estaba
    res.traducciones_nuevas += añadidas

    if es_nuevo:
        res.conceptos_nuevos += 1
    elif añadidas:
        res.conceptos_ampliados += 1
    else:
        res.sin_cambios += 1
    return None


def importar_csv(conn, ruta, area_por_defecto=""):
    """Lee el CSV y lo vuelca en la base de datos SIN hacer commit.
    Las filas con problemas se saltan y se devuelven en `errores`.
    Lanza ErrorCSV si el archivo entero no se puede usar."""
    texto, codificacion = _leer_texto(ruta)
    filas, separador, descartadas = _leer_filas(texto)
    cols, idiomas, ignoradas = _interpretar_cabecera(filas[0])
    area_por_defecto = area_por_defecto.strip()
    if cols["area"] is None and not area_por_defecto:
        raise ErrorCSV("Falta la columna 'Área'. Añádela al archivo o indica un área por defecto.")

    res = ResultadoImportacion(idiomas=list(idiomas), columnas_ignoradas=ignoradas,
                               separador=separador, codificacion=codificacion)
    for n, fila in enumerate(filas[1:], start=1):
        if not any(celda.strip() for celda in fila):
            continue                                 # fila vacía
        res.filas_leidas += 1
        linea = descartadas + 1 + n                  # nº de fila tal como la ve Excel
        error = _importar_fila(conn, fila, cols, idiomas, area_por_defecto, linea, res)
        if error:
            res.errores.append((linea, error))
    return res