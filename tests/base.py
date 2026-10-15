"""Utilidades comunes para los tests."""
import contextlib
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from gestor import basedatos, config
from gestor import menu as modulo_menu
from gestor.menu import menu


def _esta_cerrada(conn):
    try:
        conn.execute("SELECT 1")
        return False
    except sqlite3.ProgrammingError:
        return True


@contextlib.contextmanager
def conexion():
    """Abre una conexión, guarda los cambios al salir Y LA CIERRA.
    OJO: `with sqlite3.connect(...) as conn:` solo guarda, no cierra; y en Windows
    una conexión abierta bloquea el archivo, así que no se puede borrar después."""
    with contextlib.closing(basedatos.conectar()) as conn, conn:
        yield conn


class BaseTemporal(unittest.TestCase):
    """Cada test trabaja en una carpeta temporal con su propia ruta de base de datos,
    así que NUNCA toca tu gestor_traductor.db real. La base de datos aún no existe.

    Además vigila que TODAS las conexiones que se abran (en los tests o en el propio
    programa) se cierren: en Windows, una conexión abierta impide borrar la carpeta
    temporal. Así este fallo se detecta también en Linux y macOS."""

    def setUp(self):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)                       # se ejecuta el ÚLTIMO (orden inverso)
        self.carpeta = Path(carpeta.name)
        self.ruta_bd = self.carpeta / "test.db"
        parche = mock.patch.object(config, "DB_PATH", self.ruta_bd)
        parche.start()
        self.addCleanup(parche.stop)

        self._conexiones = []
        self.addCleanup(self._comprobar_conexiones_cerradas)   # justo antes de borrar la carpeta
        original = basedatos.conectar

        def conectar_vigilado():
            conn = original()
            self._conexiones.append(conn)
            return conn

        for modulo in (basedatos, modulo_menu):                # menu.py importó 'conectar' por nombre
            parche = mock.patch.object(modulo, "conectar", conectar_vigilado)
            parche.start()
            self.addCleanup(parche.stop)

    def _comprobar_conexiones_cerradas(self):
        abiertas = [c for c in self._conexiones if not _esta_cerrada(c)]
        for c in abiertas:
            c.close()                                          # para no bloquear el borrado
        if abiertas:
            raise AssertionError(
                f"{len(abiertas)} conexión(es) a la base de datos sin cerrar "
                "(en Windows bloquean el archivo). Usa 'with closing(...)' o conexion().")

    def volcado(self):
        """Todo el contenido como lista ordenada de (área, definición, idioma, término)."""
        with conexion() as conn:
            return volcado(conn)


class BaseConBD(BaseTemporal):
    """Como BaseTemporal, pero con la base de datos ya creada y `self.conn` abierta."""

    def setUp(self):
        super().setUp()
        basedatos.inicializar_bd()
        self.conn = basedatos.conectar()
        self.addCleanup(self.conn.close)          # se cierra ANTES de borrar la carpeta


def volcado(conn):
    return sorted(tuple(r) for r in conn.execute(
        "SELECT c.area, c.definicion, t.idioma, t.termino "
        "FROM Conceptos c JOIN Terminos t USING (id_concepto)"))


def correr_menu(entradas):
    """Ejecuta el menú con respuestas simuladas y devuelve lo que se imprimió.
    Añade un '0' (Salir) al final para que siempre termine."""
    respuestas = iter(list(entradas) + ["0"])
    salida = io.StringIO()
    with mock.patch("builtins.input", lambda *_: next(respuestas)), \
            contextlib.redirect_stdout(salida):
        menu()
    return salida.getvalue()


def crear_bd_antigua(ruta, estropeada=False):
    """Crea una base de datos con el formato ANTIGUO (Conceptos_ES + Traducciones),
    con los problemas típicos: traducciones repetidas, una marcada como 'ES',
    otra con idioma en minúsculas y otra huérfana (concepto inexistente).
    Con estropeada=True añade una tabla 'Terminos' incompatible para forzar un fallo."""
    con = sqlite3.connect(ruta)
    con.execute("""CREATE TABLE Conceptos_ES (id_concepto INTEGER PRIMARY KEY AUTOINCREMENT,
                   area TEXT, termino_es TEXT UNIQUE, definicion_es TEXT)""")
    con.execute("""CREATE TABLE Traducciones (id_traduccion INTEGER PRIMARY KEY AUTOINCREMENT,
                   id_concepto INTEGER, idioma TEXT, termino_traducido TEXT)""")
    con.executemany(
        "INSERT INTO Conceptos_ES (area, termino_es, definicion_es) VALUES (?, ?, ?)",
        [("Informática", "placa base", "Componente principal"),
         ("Política", "ONU", None),
         (None, "árbol", "Planta leñosa")])
    con.executemany(
        "INSERT INTO Traducciones (id_concepto, idioma, termino_traducido) VALUES (?, ?, ?)",
        [(1, "EN", "motherboard"), (1, "EN", "motherboard"),   # repetida
         (1, "EN", "mainboard"), (1, "FR", "carte mère"),
         (2, "ES", "no vale"),                                 # marcada como español
         (3, "en", "tree"),                                    # idioma en minúsculas
         (99, "EN", "huérfana")])                              # concepto inexistente
    if estropeada:
        con.execute("CREATE TABLE Terminos (algo TEXT)")
    con.commit()
    con.close()