import unittest
from pathlib import Path

from gestor import basedatos, intercambio as ix, repositorio as repo

from .base import BaseConBD, conexion

EJEMPLO = Path(__file__).resolve().parent.parent / "ejemplos" / "glosario_ejemplo.csv"


class Base(BaseConBD):
    def importar(self, contenido, area_defecto="", commit=True):
        """Escribe `contenido` en un CSV y lo importa (en bytes o en texto UTF-8)."""
        archivo = self.carpeta / "entrada.csv"
        archivo.write_bytes(contenido if isinstance(contenido, bytes) else contenido.encode("utf-8"))
        conn = basedatos.conectar()
        try:
            res = ix.importar_csv(conn, archivo, area_defecto)
            if commit:
                conn.commit()
            return res
        finally:
            conn.close()

    def exportar(self, nombre="salida.csv"):
        archivo = self.carpeta / nombre
        with conexion() as conn:
            return archivo, ix.exportar_csv(conn, archivo)

    def rellenar(self):
        c = self.conn
        a = repo.crear_concepto(c, "Mobiliario", "banco", "Asiento largo")
        repo.crear_traduccion(c, a, "EN", "bench"); repo.crear_traduccion(c, a, "FR", "banc")
        b = repo.crear_concepto(c, "Finanzas", "banco", "Entidad que gestiona dinero")
        repo.crear_traduccion(c, b, "EN", "bank"); repo.crear_traduccion(c, b, "EN", "bank branch")
        repo.crear_traduccion(c, b, "DE", "Bank")
        e = repo.crear_concepto(c, "Informática", "placa; base", 'Componente "principal"\ncon salto')
        repo.crear_traduccion(c, e, "EN", "motherboard")
        repo.crear_concepto(c, "Política", "ONU", "")
        c.commit()


class TestExportar(Base):
    def test_formato_para_excel(self):
        self.rellenar()
        archivo, (n, idiomas) = self.exportar()
        datos = archivo.read_bytes()
        self.assertTrue(datos.startswith(b"\xef\xbb\xbf"))                  # UTF-8 con BOM
        self.assertEqual(datos.decode("utf-8-sig").splitlines()[0], "Área;Definición;ES;DE;EN;FR")
        self.assertEqual((n, idiomas), (4, ["DE", "EN", "FR"]))
        self.assertEqual(list(self.carpeta.glob("*.tmp")), [])              # sin restos

    def test_varias_traducciones_van_en_una_celda(self):
        self.rellenar()
        archivo, _ = self.exportar()
        self.assertIn("bank | bank branch", archivo.read_text(encoding="utf-8-sig"))

    def test_base_vacia_no_crea_archivo(self):
        archivo, (n, idiomas) = self.exportar()
        self.assertEqual((n, idiomas, archivo.exists()), (0, [], False))

    def test_sobrescribir_un_archivo_existente(self):
        self.rellenar()
        archivo = self.carpeta / "salida.csv"
        archivo.write_text("viejo", encoding="utf-8")
        self.exportar()
        self.assertIn("Área;Definición", archivo.read_text(encoding="utf-8-sig"))


class TestIdaYVuelta(Base):
    def test_exportar_e_importar_en_una_base_vacia_da_los_mismos_datos(self):
        self.rellenar()
        original = self.volcado()
        archivo, _ = self.exportar()
        # vaciar la base de datos
        with conexion() as conn:
            conn.execute("DELETE FROM Conceptos")
        self.assertEqual(self.volcado(), [])
        res = self.importar(archivo.read_bytes())
        self.assertEqual((res.conceptos_nuevos, res.errores), (4, []))
        self.assertEqual(self.volcado(), original)

    def test_reimportar_lo_mismo_no_cambia_nada(self):
        self.rellenar()
        original = self.volcado()
        archivo, _ = self.exportar()
        res = self.importar(archivo.read_bytes())
        self.assertFalse(res.hay_cambios)
        self.assertEqual((res.sin_cambios, self.volcado()), (4, original))


class TestFormatosDeEntrada(Base):
    def test_google_sheets_coma_y_sin_bom(self):
        r = self.importar("Area,Definicion,ES,EN\nComida,Dulce,chocolate,chocolate\n")
        self.assertEqual((r.separador, r.codificacion, r.conceptos_nuevos), (",", "UTF-8", 1))

    def test_excel_antiguo_windows_1252(self):
        r = self.importar("Área;Definición;ES;EN\nZoología;Ave corredora;ñandú;rhea\n".encode("cp1252"))
        self.assertEqual(r.codificacion, "Windows-1252")
        self.assertIn(("Zoología", "Ave corredora", "ES", "ñandú"), self.volcado())

    def test_linea_sep_y_lineas_en_blanco_iniciales(self):
        r = self.importar("sep=;\n\nÁrea;ES;EN\nTec;router;router\n")
        self.assertEqual((r.conceptos_nuevos, r.errores), (1, []))

    def test_tabulador(self):
        r = self.importar("Área\tES\tEN\nTec\tswitch\tswitch\n")
        self.assertEqual((r.separador, r.conceptos_nuevos), ("\t", 1))

    def test_cabeceras_con_tildes_mayusculas_y_columnas_ajenas(self):
        r = self.importar("ÁREA;Definición;es;en;Notas\nTec;;hub;hub;texto cualquiera\n")
        self.assertEqual((r.conceptos_nuevos, r.idiomas, r.columnas_ignoradas), (1, ["EN"], ["Notas"]))

    def test_celdas_entrecomilladas_con_punto_y_coma_y_saltos_de_linea(self):
        self.importar('Área;Definición;ES;EN\n"Cocina; general";"Línea1\nLínea2";cuchara;spoon\n')
        self.assertIn(("Cocina; general", "Línea1\nLínea2", "ES", "cuchara"), self.volcado())

    def test_varias_traducciones_en_una_celda_sin_duplicar(self):
        self.importar("Área;ES;EN\nTec;cable;cord | cable | cord\n")
        self.assertEqual([t for _, _, i, t in self.volcado() if i == "EN"], ["cable", "cord"])

    def test_el_ejemplo_del_repositorio_se_importa_limpio(self):
        if not EJEMPLO.exists():
            self.skipTest("no está la carpeta ejemplos/")
        r = self.importar(EJEMPLO.read_bytes())
        self.assertEqual((r.errores, r.avisos), ([], []))
        self.assertGreaterEqual(r.conceptos_nuevos, 4)


class TestCabeceraIncorrecta(Base):
    def test_el_archivo_se_rechaza_y_no_se_toca_nada(self):
        casos = {
            "sin columna ES": "Área;EN\nA;b\n",
            "archivo vacío": "",
            "solo líneas en blanco": "\n\n",
            "columna repetida": "Área;ES;ES\nA;b;c\n",
            "idioma repetido": "Área;ES;EN;en\nA;b;c;d\n",
            "sin Área y sin área por defecto": "ES;EN\nb;c\n",
        }
        for nombre, contenido in casos.items():
            with self.subTest(nombre):
                with self.assertRaises(ix.ErrorCSV):
                    self.importar(contenido)
        self.assertEqual(self.volcado(), [])

    def test_archivo_inexistente(self):
        with self.assertRaises(ix.ErrorCSV):
            ix.importar_csv(self.conn, self.carpeta / "no_existe.csv")

    def test_sin_columna_area_pero_con_area_por_defecto(self):
        r = self.importar("ES;EN\ncasa;house\n", area_defecto="General")
        self.assertEqual(r.conceptos_nuevos, 1)
        self.assertIn(("General", "", "ES", "casa"), self.volcado())


class TestReglasDeLasFilas(Base):
    def setUp(self):
        super().setUp()
        self.importar("Área;Definición;ES;EN\nMobiliario;Asiento largo;banco;bench\n")

    def concepto(self, termino, definicion):
        with conexion() as conn:
            return [c for c in repo.conceptos_por_termino_es(conn, termino)
                    if c["definicion"] == definicion]

    def test_fila_sin_definicion_se_anade_al_unico_significado_existente(self):
        r = self.importar("Área;Definición;ES;EN\n;;banco;seat\n")
        self.assertEqual((r.conceptos_ampliados, r.conceptos_nuevos), (1, 0))
        self.assertIn(("Mobiliario", "Asiento largo", "EN", "seat"), self.volcado())

    def test_definicion_distinta_crea_otro_significado_y_avisa(self):
        r = self.importar("Área;Definición;ES;EN\nFinanzas;Entidad de dinero;banco;bank\n")
        self.assertEqual((r.conceptos_nuevos, len(r.avisos)), (1, 1))

    def test_fila_sin_definicion_con_varios_significados_es_un_error(self):
        self.importar("Área;Definición;ES;EN\nFinanzas;Entidad de dinero;banco;bank\n")
        antes = self.volcado()
        r = self.importar("Área;Definición;ES;EN\n;;banco;otra\n")
        self.assertEqual(len(r.errores), 1)
        self.assertIn("varios significados", r.errores[0][1])
        self.assertEqual(self.volcado(), antes)

    def test_la_definicion_se_compara_sin_distinguir_mayusculas(self):
        r = self.importar("Área;Definición;ES;EN\nMobiliario;ASIENTO LARGO;BANCO;stool\n")
        self.assertEqual((r.conceptos_ampliados, r.conceptos_nuevos), (1, 0))

    def test_filas_vacias_se_ignoran_y_las_cortas_se_aceptan(self):
        r = self.importar("Área;Definición;ES;EN\nA;d;;x\n;;;\n\nA;d2;uno\n")
        self.assertEqual((r.filas_leidas, r.conceptos_nuevos), (2, 1))
        self.assertEqual([e[1] for e in r.errores], ["falta el término en español"])

    def test_sin_area_es_un_error_salvo_que_haya_area_por_defecto(self):
        r = self.importar("Área;ES\n;sinarea\n")
        self.assertEqual([e[1] for e in r.errores], ["falta el área"])
        r = self.importar("Área;ES\n;sinarea\n", area_defecto="General")
        self.assertEqual((r.conceptos_nuevos, r.errores), (1, []))

    def test_duplicados_dentro_del_mismo_archivo_se_fusionan(self):
        r = self.importar("Área;ES;EN\nA;x1;a\nA;x1;b\nA;x1;a\n")
        self.assertEqual(r.conceptos_nuevos, 1)
        self.assertEqual([t for _, _, i, t in self.volcado() if i == "EN" and t in ("a", "b")], ["a", "b"])

    def test_el_numero_de_fila_es_el_que_ve_el_usuario_en_excel(self):
        r = self.importar("Área;ES\nA;ok\n\n;sin\n")       # cabecera=1, ok=2, vacía=3, error=4
        self.assertEqual(r.errores, [(4, "falta el área")])


class TestAvisoDeOtroSignificado(Base):
    def test_no_avisa_si_los_dos_significados_vienen_en_el_mismo_archivo(self):
        r = self.importar("Área;Definición;ES;EN\nMobiliario;Asiento;banco;bench\nFinanzas;Dinero;banco;bank\n")
        self.assertEqual((r.conceptos_nuevos, r.avisos), (2, []))

    def test_avisa_si_el_otro_significado_ya_estaba_antes(self):
        self.importar("Área;Definición;ES;EN\nMobiliario;Asiento;banco;bench\n")
        r = self.importar("Área;Definición;ES;EN\nPesca;Banco de peces;banco;shoal\n")
        self.assertEqual((r.conceptos_nuevos, len(r.avisos)), (1, 1))


class TestSinConfirmar(Base):
    def test_importar_sin_commit_no_guarda_nada(self):
        res = self.importar("Área;ES;EN\nA;temporal;t\n", commit=False)
        self.assertTrue(res.hay_cambios)              # el resumen dice que habría cambios...
        self.assertEqual(self.volcado(), [])          # ...pero no se ha guardado nada


if __name__ == "__main__":
    unittest.main()