import contextlib
import io
import sqlite3

from gestor import basedatos

from .base import BaseConBD, BaseTemporal, crear_bd_antigua


def tablas(ruta):
    with contextlib.closing(sqlite3.connect(ruta)) as con:
        return {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")}


def contar(ruta, tabla):
    with contextlib.closing(sqlite3.connect(ruta)) as con:
        return con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]


class TestBaseNueva(BaseTemporal):
    def test_crea_las_tablas_y_no_hace_copia_de_seguridad(self):
        self.assertIsNone(basedatos.inicializar_bd())
        self.assertEqual(tablas(self.ruta_bd), {"Conceptos", "Terminos"})
        self.assertEqual(list(self.carpeta.glob("*_copia_*.db")), [])

    def test_inicializar_dos_veces_no_pasa_nada(self):
        basedatos.inicializar_bd()
        self.assertIsNone(basedatos.inicializar_bd())

    def test_no_imprime_nada(self):
        # La parte de datos no habla con el usuario: de eso se encarga el menú.
        crear_bd_antigua(self.ruta_bd)
        with contextlib.redirect_stdout(io.StringIO()) as salida:
            basedatos.inicializar_bd()
        self.assertEqual(salida.getvalue(), "")


class TestMigracion(BaseTemporal):
    def setUp(self):
        super().setUp()
        crear_bd_antigua(self.ruta_bd)

    def test_se_detecta_el_formato_antiguo(self):
        self.assertTrue(basedatos.hay_formato_antiguo())

    def test_migra_los_datos_validos_y_cuenta_los_descartados(self):
        r = basedatos.inicializar_bd()
        self.assertEqual((r.conceptos, r.traducciones, r.descartadas), (3, 4, 3))
        self.assertEqual(tablas(self.ruta_bd), {"Conceptos", "Terminos"})
        self.assertEqual(self.volcado(), sorted([
            ("Informática", "Componente principal", "ES", "placa base"),
            ("Informática", "Componente principal", "EN", "motherboard"),   # sin duplicar
            ("Informática", "Componente principal", "EN", "mainboard"),
            ("Informática", "Componente principal", "FR", "carte mère"),
            ("Política", "", "ES", "ONU"),             # definición NULL -> vacía
            ("", "Planta leñosa", "ES", "árbol"),      # área NULL -> vacía
            ("", "Planta leñosa", "EN", "tree"),       # "en" -> "EN"
        ]))                                            # no están: la marcada ES ni la huérfana

    def test_hace_copia_de_seguridad_con_los_datos_originales(self):
        r = basedatos.inicializar_bd()
        self.assertTrue(r.copia.exists())
        self.assertEqual(tablas(r.copia), {"Conceptos_ES", "Traducciones"})
        self.assertEqual((contar(r.copia, "Conceptos_ES"), contar(r.copia, "Traducciones")), (3, 7))

    def test_la_segunda_vez_no_migra_ni_copia_de_nuevo(self):
        basedatos.inicializar_bd()
        self.assertIsNone(basedatos.inicializar_bd())
        self.assertEqual(len(list(self.carpeta.glob("*_copia_*.db"))), 1)
        self.assertFalse(basedatos.hay_formato_antiguo())


class TestMigracionQueFalla(BaseTemporal):
    def test_si_falla_no_se_toca_nada(self):
        crear_bd_antigua(self.ruta_bd, estropeada=True)
        with self.assertRaises(basedatos.MigracionError) as cm:
            basedatos.inicializar_bd()
        # los datos originales siguen donde estaban...
        self.assertEqual((contar(self.ruta_bd, "Conceptos_ES"), contar(self.ruta_bd, "Traducciones")), (3, 7))
        # ...no ha quedado nada a medias...
        self.assertNotIn("Conceptos", tablas(self.ruta_bd))
        # ...y la copia de seguridad existe
        self.assertTrue(cm.exception.copia.exists())


class TestConexion(BaseConBD):
    def test_las_claves_foraneas_estan_activadas(self):
        self.assertEqual(self.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_funciones_de_comparacion_registradas(self):
        fila = self.conn.execute("SELECT fold('ÁRBOL'), norm('Árbol')").fetchone()
        self.assertEqual(tuple(fila), ("árbol", "arbol"))