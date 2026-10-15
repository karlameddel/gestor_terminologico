"""Pruebas "de punta a punta": se simula a una persona tecleando en el menú."""
import os
import unittest

from .base import BaseConBD, BaseTemporal, correr_menu, crear_bd_antigua


class TestMenuBasico(BaseConBD):
    def test_anadir_y_ver_un_termino(self):
        salida = correr_menu(["1", "chocolate", "Comida", "Dulce", "3"])
        self.assertIn("Concepto 'chocolate' creado", salida)
        self.assertIn("[ES] chocolate | CATEGORÍA: Comida | DEFINICIÓN: 'Dulce'", salida)

    def test_opcion_no_valida(self):
        self.assertIn("Opción no válida", correr_menu(["x"]))

    def test_con_la_base_vacia_se_avisa(self):
        self.assertIn("Todavía no hay ningún término", correr_menu(["3"]))

    def test_campos_obligatorios_se_vuelven_a_pedir(self):
        salida = correr_menu(["1", "", "casa", "", "Hogar", ""])
        self.assertIn("no puede estar vacío", salida)
        self.assertIn(("Hogar", "", "ES", "casa"), self.volcado())

    def test_buscar(self):
        salida = correr_menu(["1", "Árbol", "Botánica", "", "4", "ARBOL"])
        self.assertIn("1 resultado(s)", salida)

    def test_borrar_pide_confirmacion(self):
        correr_menu(["1", "x", "A", "", "7", "x", "n"])
        self.assertEqual(len(self.volcado()), 1)           # dijo que no: sigue ahí
        correr_menu(["7", "x", "s"])
        self.assertEqual(self.volcado(), [])               # dijo que sí: borrado


class TestVariosSignificados(BaseConBD):
    def anadir_dos_bancos(self):
        return correr_menu(["1", "banco", "Mobiliario", "Asiento",
                            "1", "banco", "s", "Finanzas", "", "Dinero"])

    def test_el_segundo_significado_exige_definicion(self):
        salida = self.anadir_dos_bancos()
        self.assertIn("la definición es obligatoria", salida)
        self.assertIn("no puede estar vacío", salida)
        self.assertEqual(len(self.volcado()), 2)

    def test_decir_que_no_es_un_significado_nuevo_cancela(self):
        correr_menu(["1", "banco", "Mobiliario", "Asiento", "1", "banco", "n"])
        self.assertEqual(len(self.volcado()), 1)

    def test_al_traducir_se_elige_el_significado(self):
        self.anadir_dos_bancos()
        salida = correr_menu(["2", "banco", "2", "EN", "bank"])
        self.assertIn("tiene 2 significados", salida)
        self.assertIn(("Finanzas", "Dinero", "EN", "bank"), self.volcado())
        self.assertNotIn(("Mobiliario", "Asiento", "EN", "bank"), self.volcado())


class TestMenuCsv(BaseConBD):
    def setUp(self):
        super().setUp()
        previo = os.getcwd()
        os.chdir(self.carpeta)                       # los archivos se crean aquí, no en tu proyecto
        self.addCleanup(os.chdir, previo)

    def csv(self, contenido="Área;Definición;ES;EN\nComida;Dulce;tarta;cake\nComida;;;x\n"):
        ruta = self.carpeta / "g.csv"
        ruta.write_text(contenido, encoding="utf-8-sig")
        return str(ruta)

    def test_importar_diciendo_que_no_no_guarda(self):
        salida = correr_menu(["8", self.csv(), "", "n"])
        self.assertIn("no se ha guardado nada", salida)
        self.assertIn("1 fila(s) con problemas", salida)
        self.assertEqual(self.volcado(), [])

    def test_importar_diciendo_que_si_guarda_y_acepta_la_ruta_entre_comillas(self):
        salida = correr_menu(["8", f'"{self.csv()}"', "", "s"])
        self.assertIn("Importación guardada", salida)
        self.assertIn(("Comida", "Dulce", "ES", "tarta"), self.volcado())

    def test_reimportar_no_ofrece_guardar(self):
        correr_menu(["8", self.csv(), "", "s"])
        self.assertIn("No hay nada nuevo que guardar", correr_menu(["8", self.csv(), ""]))

    def test_errores_de_archivo_se_explican(self):
        self.assertIn("No encuentro el archivo", correr_menu(["8", str(self.carpeta / "nope.csv")]))
        self.assertIn("Falta la columna 'ES'", correr_menu(["8", self.csv("Área;EN\nA;b\n"), ""]))
        self.assertIn("Cancelado", correr_menu(["8", ""]))

    def test_exportar_anade_la_extension_y_crea_el_archivo(self):
        salida = correr_menu(["1", "casa", "Hogar", "", "9", "mi_lista"])
        archivo = self.carpeta / "mi_lista.csv"
        self.assertIn("Exportados 1 concepto(s)", salida)
        self.assertTrue(archivo.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_exportar_no_sobrescribe_si_dices_que_no(self):
        archivo = self.carpeta / "mi_lista.csv"
        archivo.write_text("CONTENIDO_ANTERIOR", encoding="utf-8")
        correr_menu(["1", "casa", "Hogar", "", "9", "mi_lista", "n"])
        self.assertEqual(archivo.read_text(encoding="utf-8"), "CONTENIDO_ANTERIOR")

    def test_exportar_con_la_base_vacia(self):
        salida = correr_menu(["9", "vacio"])
        self.assertIn("No hay términos que exportar", salida)
        self.assertFalse((self.carpeta / "vacio.csv").exists())


class TestMigracionDesdeElMenu(BaseTemporal):
    def test_avisa_de_la_migracion_y_de_la_copia_de_seguridad(self):
        crear_bd_antigua(self.ruta_bd)
        salida = correr_menu([])
        self.assertIn("formato antiguo", salida)
        self.assertIn("Migrados 3 término(s) y 4 traducción(es)", salida)
        self.assertIn("3 traducción(es) repetidas o inválidas", salida)
        self.assertEqual(len(list(self.carpeta.glob("*_copia_*.db"))), 1)

    def test_si_la_migracion_falla_sale_con_un_mensaje_claro(self):
        crear_bd_antigua(self.ruta_bd, estropeada=True)
        with self.assertRaises(SystemExit) as cm:
            correr_menu([])
        self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()