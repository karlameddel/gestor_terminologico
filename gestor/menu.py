"""Interfaz de texto: el menú y lo que se pregunta y se muestra en cada opción.
Aquí no hay SQL; los datos se consultan y modifican a través de `repositorio`."""
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path

from . import intercambio, repositorio as repo
from .basedatos import MigracionError, conectar, hay_formato_antiguo, inicializar_bd
from .entrada import (pedir_confirmacion, pedir_con_valor_actual,
                      pedir_numero, pedir_ruta, pedir_texto)


# ---------- Utilidades de presentación ----------

def pedir_idioma(mensaje="Idioma destino (ej. FR, EN): "):
    while True:
        codigo = input(mensaje).strip().upper()
        error = repo.validar_idioma(codigo)
        if error is None:
            return codigo
        print(f"⚠️  {error}")


def descripcion_significado(c):
    return f"[{c['area']}] {c['definicion'] or 'sin definición'}"


def mostrar_concepto(conn, c):
    definicion = c["definicion"] or "sin definición"
    print(f"\n [ES] {c['termino_es']} | CATEGORÍA: {c['area']} | DEFINICIÓN: '{definicion}'")
    for t in repo.obtener_traducciones(conn, c["id_concepto"]):
        print(f"   ↳ {t['idioma']}: {t['termino']}")


def elegir_concepto(conn, mensaje):
    """Pide un término en español. Si tiene varios significados, deja elegir uno.
    Devuelve la fila del concepto o None."""
    texto = pedir_texto(mensaje)
    candidatos = repo.conceptos_por_termino_es(conn, texto)
    if not candidatos:
        print("No existe ese término en español. Créalo primero en la opción 1.")
        return None
    if len(candidatos) == 1:
        return candidatos[0]

    print(f"\n'{candidatos[0]['termino_es']}' tiene {len(candidatos)} significados:")
    for i, c in enumerate(candidatos, start=1):
        print(f"  {i}. {descripcion_significado(c)}")
    n = pedir_numero("¿Cuál? (número, Enter para cancelar): ", len(candidatos))
    if n is None:
        print("Cancelado.")
        return None
    return candidatos[n - 1]


# ---------- Opciones del menú ----------

def añadir_concepto_origen():
    print("\n--- 1. Nuevo Término (Origen: Español) ---")
    termino = pedir_texto("Término en Español: ")

    with closing(conectar()) as conn, conn:
        existentes = repo.conceptos_por_termino_es(conn, termino)
        if existentes:
            print(f"\nYa existe '{termino}' con estos significados:")
            for c in existentes:
                print(f"  - {descripcion_significado(c)}")
            if not pedir_confirmacion("¿Quieres añadir un significado NUEVO y distinto?"):
                print("Cancelado.")
                return
            print("Para distinguirlo de los demás, la definición es obligatoria.")

        area = pedir_texto("Área (ej. Comida): ")
        if existentes:
            definicion = pedir_texto("Definición: ")
        else:
            definicion = pedir_texto("Definición (puedes dejarla vacía): ", obligatorio=False)

        if repo.hay_significado_repetido(conn, termino, definicion):
            print("AVISO: Ya existe ese término con esa misma definición. No se ha guardado.")
            return

        repo.crear_concepto(conn, area, termino, definicion)
    print(f"✅ Concepto '{termino}' creado correctamente.")


def añadir_traduccion():
    print("\n--- 2. Añadir Traducción ---")
    with closing(conectar()) as conn, conn:
        concepto = elegir_concepto(
            conn, "¿De qué término en ESPAÑOL quieres añadir la traducción?: ")
        if concepto is None:
            return

        idioma = pedir_idioma()
        traduccion = pedir_texto("Término traducido: ")

        try:
            repo.crear_traduccion(conn, concepto["id_concepto"], idioma, traduccion)
            print(f"✅ Traducción guardada: {concepto['termino_es']} (ES) -> {traduccion} ({idioma})")
        except sqlite3.IntegrityError:
            print("AVISO: Esa traducción ya existe para este término.")


def ver_diccionario_completo():
    print("\n--- DICCIONARIO COMPLETO ---")
    with closing(conectar()) as conn:
        conceptos = repo.listar_conceptos(conn)
        if not conceptos:
            print("(Todavía no hay ningún término. Añade uno con la opción 1.)")
            return
        for c in conceptos:
            mostrar_concepto(conn, c)


def buscar():
    print("\n--- 4. Buscar ---")
    print("Busca en términos, definiciones, áreas y traducciones.")
    print("No importan las mayúsculas ni las tildes, y vale una parte de la palabra.")
    texto = pedir_texto("Buscar: ")

    with closing(conectar()) as conn:
        resultados = repo.buscar_conceptos(conn, texto)
        if not resultados:
            print(f"Sin resultados para '{texto}'.")
            return
        print(f"\n{len(resultados)} resultado(s) para '{texto}':")
        for c in resultados:
            mostrar_concepto(conn, c)


def editar_concepto():
    print("\n--- 5. Editar un término ---")
    with closing(conectar()) as conn, conn:
        concepto = elegir_concepto(conn, "¿Qué término en ESPAÑOL quieres editar?: ")
        if concepto is None:
            return

        print("Pulsa Enter para dejar un campo como está. "
              "En la definición, escribe '-' para vaciarla.")
        area = pedir_con_valor_actual("Área", concepto["area"])
        termino = pedir_con_valor_actual("Término", concepto["termino_es"])
        definicion = pedir_con_valor_actual("Definición", concepto["definicion"])
        if definicion == "-":
            definicion = ""

        if repo.hay_significado_repetido(conn, termino, definicion, concepto["id_concepto"]):
            print("AVISO: Ya existe otro concepto con ese término y esa definición. "
                  "No se ha cambiado nada.")
            return

        repo.actualizar_concepto(conn, concepto["id_concepto"], area, termino, definicion)
        print("✅ Término actualizado.")


def gestionar_traducciones():
    print("\n--- 6. Editar o borrar una traducción ---")
    with closing(conectar()) as conn, conn:
        concepto = elegir_concepto(conn, "¿De qué término en ESPAÑOL?: ")
        if concepto is None:
            return

        traducciones = repo.obtener_traducciones(conn, concepto["id_concepto"])
        if not traducciones:
            print("Este término todavía no tiene traducciones.")
            return

        print(f"\nTraducciones de '{concepto['termino_es']}':")
        for i, t in enumerate(traducciones, start=1):
            print(f"  {i}. {t['idioma']}: {t['termino']}")

        n = pedir_numero("¿Cuál? (número, Enter para cancelar): ", len(traducciones))
        if n is None:
            print("Cancelado.")
            return
        elegida = traducciones[n - 1]

        accion = input("¿Editar (e) o borrar (b)?: ").strip().lower()
        if accion == "b":
            if pedir_confirmacion(f"¿Borrar '{elegida['termino']}' ({elegida['idioma']})?"):
                repo.borrar_traduccion(conn, elegida["id_termino"])
                print("🗑️  Traducción borrada.")
            else:
                print("Cancelado.")
        elif accion == "e":
            idioma = pedir_con_valor_actual("Idioma", elegida["idioma"]).upper()
            error = repo.validar_idioma(idioma)
            if error:
                print(f"⚠️  {error} No se ha cambiado nada.")
                return
            texto = pedir_con_valor_actual("Término traducido", elegida["termino"])
            try:
                repo.actualizar_traduccion(conn, elegida["id_termino"], idioma, texto)
                print("✅ Traducción actualizada.")
            except sqlite3.IntegrityError:
                print("AVISO: Ya existe esa traducción para este término. No se ha cambiado nada.")
        else:
            print("Cancelado.")


def borrar_concepto():
    print("\n--- 7. Borrar un término ---")
    with closing(conectar()) as conn, conn:
        concepto = elegir_concepto(conn, "¿Qué término en ESPAÑOL quieres borrar?: ")
        if concepto is None:
            return

        mostrar_concepto(conn, concepto)
        n = len(repo.obtener_traducciones(conn, concepto["id_concepto"]))
        aviso = f" y sus {n} traducción(es)" if n else ""
        if not pedir_confirmacion(f"\n¿Seguro que quieres borrar este significado de "
                                  f"'{concepto['termino_es']}'{aviso}? No se puede deshacer"):
            print("Cancelado.")
            return

        repo.borrar_concepto(conn, concepto["id_concepto"])
        print("🗑️  Término borrado.")


def _mostrar_lineas(titulo, lineas, maximo=10):
    """Imprime una lista de (nº de fila, mensaje), recortada si es muy larga."""
    print(titulo)
    for n, mensaje in lineas[:maximo]:
        print(f"     - fila {n}: {mensaje}")
    if len(lineas) > maximo:
        print(f"     ... y {len(lineas) - maximo} más")


def mostrar_resumen_importacion(res):
    sep = "tabulador" if res.separador == "\t" else f"'{res.separador}'"
    print(f"\n📄 {res.filas_leidas} fila(s) leída(s) · separador {sep} · codificación {res.codificacion}")
    print("   Idiomas detectados: " + ", ".join(["ES"] + res.idiomas))
    if res.columnas_ignoradas:
        print("   Columnas ignoradas: " + ", ".join(res.columnas_ignoradas))
    print(f"\n   ➕ {res.conceptos_nuevos} concepto(s) nuevo(s)")
    print(f"   🔁 {res.conceptos_ampliados} concepto(s) existente(s) ampliado(s) con traducciones")
    print(f"   🌐 {res.traducciones_nuevas} traducción(es) añadida(s) en total")
    print(f"   ✔️  {res.sin_cambios} fila(s) que ya estaban en el diccionario")
    if res.avisos:
        _mostrar_lineas("\nℹ️  Conviene revisar:", res.avisos)
    if res.errores:
        _mostrar_lineas(f"\n⚠️  {len(res.errores)} fila(s) con problemas que NO se importarán:", res.errores)


def importar_desde_csv():
    print("\n--- 8. Importar desde CSV (Excel / Google Sheets) ---")
    print("Columnas: Área, Definición, ES y una columna por idioma (EN, FR...).")
    print("Varias traducciones en una celda se separan con |   (ej. motherboard | mainboard)")
    ruta = pedir_ruta("Archivo CSV (Enter para cancelar): ")
    if ruta is None:
        print("Cancelado.")
        return
    if not ruta.is_file():
        print(f"⚠️  No encuentro el archivo: {ruta}")
        return
    area_defecto = pedir_texto("Área para las filas que no tengan (Enter = rechazarlas): ",
                               obligatorio=False)

    # Nada se guarda hasta que se confirma: al cerrar la conexión sin commit,
    # SQLite descarta todo lo importado.
    with closing(conectar()) as conn:
        try:
            res = intercambio.importar_csv(conn, ruta, area_defecto)
        except intercambio.ErrorCSV as e:
            print(f"❌ {e}")
            return
        mostrar_resumen_importacion(res)
        if not res.hay_cambios:
            print("\nNo hay nada nuevo que guardar.")
            return
        if pedir_confirmacion("\n¿Guardar estos cambios?"):
            conn.commit()
            print("✅ Importación guardada.")
        else:
            conn.rollback()
            print("Cancelado: no se ha guardado nada.")


def exportar_a_csv():
    print("\n--- 9. Exportar a CSV (Excel / Google Sheets) ---")
    sugerido = f"glosario_{date.today():%Y-%m-%d}.csv"
    ruta = pedir_ruta(f"Nombre del archivo (Enter = {sugerido}): ") or Path(sugerido)
    if ruta.suffix.lower() != ".csv":
        ruta = ruta.with_name(ruta.name + ".csv")
    if ruta.exists() and not pedir_confirmacion(f"'{ruta.name}' ya existe. ¿Sobrescribirlo?"):
        print("Cancelado.")
        return

    with closing(conectar()) as conn:
        try:
            n, idiomas = intercambio.exportar_csv(conn, ruta)
        except OSError as e:
            print(f"❌ No se pudo guardar el archivo ({e.strerror or e}).")
            print("   ¿Lo tienes abierto en Excel? Ciérralo e inténtalo de nuevo.")
            return
    if n == 0:
        print("No hay términos que exportar todavía.")
        return
    print(f"✅ Exportados {n} concepto(s) con los idiomas: {', '.join(['ES'] + idiomas)}")
    print(f"   Archivo: {ruta.resolve()}")


def preparar_base_de_datos():
    """Crea o actualiza la base de datos y cuenta al usuario lo que haya pasado."""
    if hay_formato_antiguo():
        print("🔄 Se ha detectado una base de datos con el formato antiguo. Actualizando...")
    try:
        resultado = inicializar_bd()
    except MigracionError as e:
        print(f"❌ No se pudo actualizar la base de datos: {e}")
        print(f"   Tus datos originales no se han modificado. Copia de seguridad: {e.copia.name}")
        raise SystemExit(1)
    if resultado:
        print(f"✅ Migrados {resultado.conceptos} término(s) y {resultado.traducciones} "
              f"traducción(es). Copia de seguridad: {resultado.copia.name}")
        if resultado.descartadas:
            print(f"   ({resultado.descartadas} traducción(es) repetidas o inválidas "
                  "no se han copiado.)")


def menu():
    preparar_base_de_datos()
    opciones = {
        "1": añadir_concepto_origen,
        "2": añadir_traduccion,
        "3": ver_diccionario_completo,
        "4": buscar,
        "5": editar_concepto,
        "6": gestionar_traducciones,
        "7": borrar_concepto,
        "8": importar_desde_csv,
        "9": exportar_a_csv,
    }
    while True:
        print("\n=== GESTOR TERMINOLÓGICO (Modelo Origen-Destino) ===")
        print("1. Añadir nuevo término en español (Origen)")
        print("2. Añadir Traducción a un término existente")
        print("3. Ver diccionario completo")
        print("4. Buscar")
        print("5. Editar un término")
        print("6. Editar o borrar una traducción")
        print("7. Borrar un término")
        print("8. Importar desde CSV (Excel / Google Sheets)")
        print("9. Exportar a CSV (Excel / Google Sheets)")
        print("0. Salir")

        op = input("Selecciona: ").strip()
        if op == "0":
            break
        accion = opciones.get(op)
        if accion:
            accion()
        else:
            print("⚠️  Opción no válida. Elige una opción del menú (0-9).")