import sqlite3

from gestor import repositorio as repo

from .base import BaseConBD


class Base(BaseConBD):
    def crear(self, area, es, definicion="", traducciones=()):
        id_ = repo.crear_concepto(self.conn, area, es, definicion)
        for idioma, termino in traducciones:
            repo.crear_traduccion(self.conn, id_, idioma, termino)
        return id_


class TestIdiomas(Base):
    def test_codigos_validos(self):
        for codigo in ("EN", "fr", " de ", "ZHO"):
            with self.subTest(codigo=codigo):
                self.assertIsNone(repo.validar_idioma(codigo))

    def test_codigos_no_validos(self):
        for codigo in ("", "E", "ENGL", "E1", "--"):
            with self.subTest(codigo=codigo):
                self.assertIsNotNone(repo.validar_idioma(codigo))

    def test_el_espanol_no_vale_como_traduccion_en_ninguna_capitalizacion(self):
        for codigo in ("ES", "es", "Es"):
            with self.subTest(codigo=codigo):
                self.assertIn("origen", repo.validar_idioma(codigo))
                id_ = self.crear("A", "casa")
                with self.assertRaises(ValueError):
                    repo.crear_traduccion(self.conn, id_, codigo, "x")

    def test_el_idioma_se_guarda_en_mayusculas(self):
        id_ = self.crear("A", "casa")
        repo.crear_traduccion(self.conn, id_, " en ", "house")
        self.assertEqual([t["idioma"] for t in repo.obtener_traducciones(self.conn, id_)], ["EN"])


class TestConceptos(Base):
    def test_crear_concepto_guarda_su_termino_en_espanol(self):
        id_ = self.crear("Comida", "tarta", "Dulce")
        fila = self.conn.execute(
            "SELECT idioma, termino FROM Terminos WHERE id_concepto = ?", (id_,)).fetchone()
        self.assertEqual(tuple(fila), ("ES", "tarta"))

    def test_buscar_por_termino_ignora_mayusculas_y_tildes_en_mayuscula(self):
        self.crear("Botánica", "Árbol")
        self.assertEqual(len(repo.conceptos_por_termino_es(self.conn, "ÁRBOL")), 1)

    def test_buscar_por_termino_si_distingue_la_tilde(self):
        # Decisión de diseño: "arbol" y "árbol" son palabras distintas.
        self.crear("Botánica", "árbol")
        self.assertEqual(repo.conceptos_por_termino_es(self.conn, "arbol"), [])

    def test_varios_significados_del_mismo_termino(self):
        self.crear("Finanzas", "banco", "Entidad de dinero")
        self.crear("Mobiliario", "banco", "Asiento largo")
        encontrados = repo.conceptos_por_termino_es(self.conn, "BANCO")
        self.assertEqual([c["definicion"] for c in encontrados],
                         ["Asiento largo", "Entidad de dinero"])   # ordenados por definición

    def test_significado_repetido(self):
        id_ = self.crear("Mobiliario", "banco", "Asiento largo")
        self.assertTrue(repo.hay_significado_repetido(self.conn, "BANCO", "asiento LARGO"))
        self.assertFalse(repo.hay_significado_repetido(self.conn, "banco", "Entidad de dinero"))
        self.assertFalse(repo.hay_significado_repetido(self.conn, "mesa", "Asiento largo"))
        # al editar un concepto, no choca consigo mismo
        self.assertFalse(repo.hay_significado_repetido(self.conn, "banco", "Asiento largo", id_))

    def test_dos_conceptos_sin_definicion_cuentan_como_repetidos(self):
        self.crear("A", "casa")
        self.assertTrue(repo.hay_significado_repetido(self.conn, "Casa", ""))

    def test_listar_ordena_alfabeticamente_sin_que_las_tildes_molesten(self):
        for termino in ("Zorro", "Árbol", "Abeja", "Óvalo", "ñandú"):
            self.crear("A", termino)
        self.assertEqual([c["termino_es"] for c in repo.listar_conceptos(self.conn)],
                         ["Abeja", "Árbol", "ñandú", "Óvalo", "Zorro"])

    def test_actualizar_concepto(self):
        id_ = self.crear("A", "casa", "vieja")
        repo.actualizar_concepto(self.conn, id_, "Hogar", "vivienda", "nueva")
        c = repo.conceptos_por_termino_es(self.conn, "vivienda")[0]
        self.assertEqual((c["area"], c["definicion"]), ("Hogar", "nueva"))

    def test_borrar_concepto_borra_tambien_sus_terminos(self):
        id_ = self.crear("A", "casa", traducciones=[("EN", "house"), ("FR", "maison")])
        otro = self.crear("A", "perro", traducciones=[("EN", "dog")])
        repo.borrar_concepto(self.conn, id_)
        restantes = self.conn.execute("SELECT DISTINCT id_concepto FROM Terminos").fetchall()
        self.assertEqual([r[0] for r in restantes], [otro])


class TestBusqueda(Base):
    def setUp(self):
        super().setUp()
        self.crear("Informática", "placa base", "Componente principal",
                   [("EN", "motherboard"), ("FR", "carte mère")])
        self.crear("Botánica", "árbol", "Planta leñosa", [("EN", "tree")])

    def buscar(self, texto):
        return [c["termino_es"] for c in repo.buscar_conceptos(self.conn, texto)]

    def test_por_termino_parcial(self):
        # "pla" está en "placa base" (término) y en "Planta leñosa" (definición de árbol)
        self.assertEqual(self.buscar("pla"), ["árbol", "placa base"])

    def test_por_traduccion(self):
        self.assertEqual(self.buscar("mother"), ["placa base"])

    def test_sin_escribir_la_tilde_ni_la_mayuscula(self):
        self.assertEqual(self.buscar("ARBOL"), ["árbol"])
        self.assertEqual(self.buscar("lenosa"), ["árbol"])              # definición con ñ
        self.assertEqual(self.buscar("INFORMATICA"), ["placa base"])    # área

    def test_sin_resultados(self):
        self.assertEqual(self.buscar("zzz"), [])

    def test_caracteres_especiales_no_valen_como_comodin(self):
        self.assertEqual(self.buscar("%"), [])
        self.assertEqual(self.buscar("_"), [])


class TestTraducciones(Base):
    def setUp(self):
        super().setUp()
        self.id = self.crear("A", "placa base")

    def textos(self):
        return [(t["idioma"], t["termino"]) for t in repo.obtener_traducciones(self.conn, self.id)]

    def test_varias_traducciones_en_el_mismo_idioma(self):
        repo.crear_traduccion(self.conn, self.id, "EN", "motherboard")
        repo.crear_traduccion(self.conn, self.id, "EN", "mainboard")
        repo.crear_traduccion(self.conn, self.id, "FR", "carte mère")
        self.assertEqual(self.textos(),
                         [("EN", "mainboard"), ("EN", "motherboard"), ("FR", "carte mère")])

    def test_traduccion_repetida(self):
        repo.crear_traduccion(self.conn, self.id, "EN", "motherboard")
        with self.assertRaises(sqlite3.IntegrityError):
            repo.crear_traduccion(self.conn, self.id, "en", "motherboard")

    def test_la_lista_de_traducciones_no_incluye_el_termino_en_espanol(self):
        self.assertEqual(self.textos(), [])

    def test_actualizar_traduccion(self):
        repo.crear_traduccion(self.conn, self.id, "EN", "motherboard")
        id_t = repo.obtener_traducciones(self.conn, self.id)[0]["id_termino"]
        repo.actualizar_traduccion(self.conn, id_t, "de", "Hauptplatine")
        self.assertEqual(self.textos(), [("DE", "Hauptplatine")])

    def test_actualizar_traduccion_a_una_que_ya_existe(self):
        repo.crear_traduccion(self.conn, self.id, "EN", "a")
        repo.crear_traduccion(self.conn, self.id, "EN", "b")
        id_b = [t for t in repo.obtener_traducciones(self.conn, self.id)
                if t["termino"] == "b"][0]["id_termino"]
        with self.assertRaises(sqlite3.IntegrityError):
            repo.actualizar_traduccion(self.conn, id_b, "EN", "a")

    def test_borrar_traduccion(self):
        repo.crear_traduccion(self.conn, self.id, "EN", "a")
        repo.crear_traduccion(self.conn, self.id, "EN", "b")
        repo.borrar_traduccion(self.conn, repo.obtener_traducciones(self.conn, self.id)[0]["id_termino"])
        self.assertEqual(self.textos(), [("EN", "b")])


class TestReglasDeLaBaseDeDatos(Base):
    """Reglas que garantiza SQLite por sí mismo, aunque el código se equivoque."""

    def test_un_concepto_no_puede_tener_dos_terminos_en_espanol(self):
        id_ = self.crear("A", "casa")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO Terminos (id_concepto, idioma, termino) "
                              "VALUES (?, 'ES', 'hogar')", (id_,))

    def test_las_claves_foraneas_estan_activas(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO Terminos (id_concepto, idioma, termino) "
                              "VALUES (999, 'EN', 'x')")