import sys
import unittest
from pathlib import Path

from gestor import config


class TestCarpetaDeDatos(unittest.TestCase):
    def test_como_programa_normal_es_la_raiz_del_proyecto(self):
        raiz = Path(config.__file__).resolve().parent.parent
        self.assertEqual(config.carpeta_de_datos(congelado=False), raiz)
        self.assertTrue((raiz / "main.py").exists())

    def test_como_exe_es_la_carpeta_del_exe_y_no_la_del_codigo(self):
        # Con PyInstaller de un solo archivo, __file__ apunta a una carpeta temporal que
        # se borra al cerrar: guardar ahí la base de datos haría perder todos los datos.
        exe = Path("/programas/gestor/GestorTerminologico.exe")
        self.assertEqual(config.carpeta_de_datos(congelado=True, ejecutable=str(exe)),
                         exe.resolve().parent)

    def test_se_detecta_solo_que_esta_empaquetado(self):
        self.assertFalse(getattr(sys, "frozen", False))      # los tests corren con Python normal
        self.assertEqual(config.carpeta_de_datos(), config.carpeta_de_datos(congelado=False))

    def test_la_base_de_datos_se_llama_igual_que_siempre(self):
        self.assertEqual(config.DB_PATH.name, "gestor_traductor.db")


if __name__ == "__main__":
    unittest.main()