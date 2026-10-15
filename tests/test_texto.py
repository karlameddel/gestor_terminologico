import unittest

from gestor.texto import fold, norm


class TestFold(unittest.TestCase):
    def test_ignora_mayusculas_tambien_con_tildes_y_enie(self):
        # SQLite por sí solo NO distingue "a" de "A", pero SÍ "á" de "Á".
        self.assertEqual(fold("Árbol"), fold("árbol"))
        self.assertEqual(fold("ÑANDÚ"), fold("ñandú"))

    def test_conserva_las_tildes(self):
        self.assertNotEqual(fold("arbol"), fold("árbol"))

    def test_casefold_de_otros_idiomas(self):
        self.assertEqual(fold("Straße"), fold("STRASSE"))

    def test_none_es_cadena_vacia(self):
        self.assertEqual(fold(None), "")


class TestNorm(unittest.TestCase):
    def test_quita_tildes_y_dieresis(self):
        self.assertEqual(norm("Informática"), "informatica")
        self.assertEqual(norm("Über"), "uber")

    def test_la_enie_cuenta_como_n(self):
        self.assertEqual(norm("ñandú"), "nandu")

    def test_none_es_cadena_vacia(self):
        self.assertEqual(norm(None), "")


if __name__ == "__main__":
    unittest.main()