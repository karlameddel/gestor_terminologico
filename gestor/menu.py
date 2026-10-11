"""Interfaz de texto: el menú y lo que se pregunta y se muestra en cada opción.
Aquí no hay SQL; los datos se consultan y modifican a través de `repositorio`."""
import sqlite3
from contextlib import closing

from . import repositorio as repo
from .basedatos import conectar, inicializar_bd
from .entrada import (pedir_confirmacion, pedir_con_valor_actual,
                      pedir_numero, pedir_texto)


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


def menu():
    inicializar_bd()
    opciones = {
        "1": añadir_concepto_origen,
        "2": añadir_traduccion,
        "3": ver_diccionario_completo,
        "4": buscar,
        "5": editar_concepto,
        "6": gestionar_traducciones,
        "7": borrar_concepto,
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
        print("8. Salir")

        op = input("Selecciona: ").strip()
        if op == "8":
            break
        accion = opciones.get(op)
        if accion:
            accion()
        else:
            print("⚠️  Opción no válida. Elige un número del 1 al 8.")