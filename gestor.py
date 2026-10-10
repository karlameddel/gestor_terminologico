import sqlite3
import unicodedata
from contextlib import closing
from pathlib import Path

# La base de datos se guarda junto a este archivo, se ejecute desde donde se ejecute.
DB_PATH = Path(__file__).with_name("gestor_traductor.db")


# ---------- Comparación de textos ----------
# Ojo: SQLite solo ignora mayúsculas en letras ASCII (COLLATE NOCASE y LIKE
# no distinguen "a" de "A", pero SÍ distinguen "á" de "Á" o "ñ" de "Ñ").
# Para un gestor en varios idiomas necesitamos algo mejor, así que le
# enseñamos a SQLite dos funciones propias:

def _fold(texto):
    """Minúsculas 'inteligentes' (Árbol == árbol, Straße == strasse)."""
    return (texto or "").casefold()


def _norm(texto):
    """Como _fold, y además sin tildes ni diéresis: 'Informática' -> 'informatica'.
    Se usa para buscar sin preocuparse de si se escribió la tilde."""
    descompuesto = unicodedata.normalize("NFD", _fold(texto))
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def conectar():
    conn = sqlite3.connect(DB_PATH)
    # SQLite no comprueba las claves foráneas si no se le pide explícitamente.
    conn.execute("PRAGMA foreign_keys = ON")
    # Permite acceder a las columnas por nombre: fila["termino_es"]
    conn.row_factory = sqlite3.Row
    conn.create_function("fold", 1, _fold, deterministic=True)
    conn.create_function("norm", 1, _norm, deterministic=True)
    return conn


def inicializar_bd():
    # `with conn` hace commit si todo va bien y rollback si hay un error.
    # `closing` cierra la conexión al terminar en cualquier caso.
    with closing(conectar()) as conn, conn:
        # TABLA 1: El idioma origen (Español como base)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Conceptos_ES (
                id_concepto   INTEGER PRIMARY KEY AUTOINCREMENT,
                area          TEXT,
                termino_es    TEXT UNIQUE COLLATE NOCASE,
                definicion_es TEXT
            )""")

        # TABLA 2: Las traducciones conectadas al término en español
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Traducciones (
                id_traduccion     INTEGER PRIMARY KEY AUTOINCREMENT,
                id_concepto       INTEGER NOT NULL,
                idioma            TEXT NOT NULL,
                termino_traducido TEXT NOT NULL,
                FOREIGN KEY (id_concepto) REFERENCES Conceptos_ES(id_concepto),
                UNIQUE (id_concepto, idioma, termino_traducido)
            )""")


# ---------- Utilidades de entrada ----------

def pedir_texto(mensaje, obligatorio=True):
    """Pide un texto por pantalla. Si es obligatorio, repite hasta que no esté vacío."""
    while True:
        valor = input(mensaje).strip()
        if valor or not obligatorio:
            return valor
        print("⚠️  Este campo no puede estar vacío.")


def pedir_idioma(mensaje="Idioma destino (ej. FR, EN): "):
    """Pide un código de idioma de 2 o 3 letras (EN, FR, DE, ...)."""
    while True:
        codigo = input(mensaje).strip().upper()
        if codigo.isalpha() and 2 <= len(codigo) <= 3:
            return codigo
        print("⚠️  Escribe un código de 2 o 3 letras (ej. EN, FR, DE).")


def pedir_confirmacion(mensaje):
    """Pregunta sí/no. Devuelve True solo si responde 's'."""
    while True:
        r = input(f"{mensaje} (s/n): ").strip().lower()
        if r in ("s", "si", "sí"):
            return True
        if r in ("n", "no"):
            return False
        print("⚠️  Responde 's' o 'n'.")


def pedir_numero(mensaje, maximo):
    """Pide un número entre 1 y `maximo`. Enter vacío cancela (devuelve None)."""
    while True:
        r = input(mensaje).strip()
        if not r:
            return None
        if r.isdigit() and 1 <= int(r) <= maximo:
            return int(r)
        print(f"⚠️  Escribe un número entre 1 y {maximo} (o Enter para cancelar).")


def pedir_con_valor_actual(etiqueta, actual):
    """Para editar: Enter deja el valor como está."""
    nuevo = input(f"{etiqueta} [{actual}]: ").strip()
    return nuevo or actual


# ---------- Consultas y presentación (reutilizables) ----------

def buscar_concepto_por_termino(conn, texto):
    """Busca un concepto por su término en español, ignorando mayúsculas."""
    return conn.execute(
        "SELECT id_concepto, area, termino_es, definicion_es FROM Conceptos_ES "
        "WHERE fold(termino_es) = fold(?)",
        (texto,),
    ).fetchone()


def pedir_concepto_existente(conn, mensaje):
    """Pide un término en español y devuelve su fila, o None si no existe."""
    texto = pedir_texto(mensaje)
    fila = buscar_concepto_por_termino(conn, texto)
    if fila is None:
        print("No existe ese término en español. Créalo primero en la opción 1.")
    return fila


def obtener_traducciones(conn, id_concepto):
    return conn.execute(
        "SELECT id_traduccion, idioma, termino_traducido FROM Traducciones "
        "WHERE id_concepto = ? ORDER BY idioma, termino_traducido",
        (id_concepto,),
    ).fetchall()


def mostrar_concepto(conn, c):
    definicion = c["definicion_es"] or "sin definición"
    print(f"\n [ES] {c['termino_es']} | CATEGORÍA: {c['area']} | DEFINICIÓN: '{definicion}'")
    for t in obtener_traducciones(conn, c["id_concepto"]):
        print(f"   ↳ {t['idioma']}: {t['termino_traducido']}")


# ---------- Opciones del menú ----------

def añadir_concepto_origen():
    print("\n--- 1. Nuevo Término (Origen: Español) ---")
    area = pedir_texto("Área (ej. Comida): ")
    termino = pedir_texto("Término en Español: ")
    definicion = pedir_texto("Definición (puedes dejarla vacía): ", obligatorio=False)

    try:
        with closing(conectar()) as conn, conn:
            if buscar_concepto_por_termino(conn, termino):
                print("AVISO: Ese término en español ya existe en la base de datos.")
                return
            conn.execute(
                "INSERT INTO Conceptos_ES (area, termino_es, definicion_es) VALUES (?, ?, ?)",
                (area, termino, definicion),
            )
        print(f"✅ Concepto '{termino}' creado correctamente.")
    except sqlite3.IntegrityError:
        print("AVISO: Ese término en español ya existe en la base de datos.")


def añadir_traduccion():
    print("\n--- 2. Añadir Traducción ---")
    with closing(conectar()) as conn, conn:
        concepto = pedir_concepto_existente(
            conn, "¿De qué término en ESPAÑOL quieres añadir la traducción?: ")
        if concepto is None:
            return

        idioma = pedir_idioma()
        traduccion = pedir_texto("Término traducido: ")

        try:
            conn.execute(
                "INSERT INTO Traducciones (id_concepto, idioma, termino_traducido) "
                "VALUES (?, ?, ?)",
                (concepto["id_concepto"], idioma, traduccion),
            )
            print(f"✅ Traducción guardada: {concepto['termino_es']} (ES) -> {traduccion} ({idioma})")
        except sqlite3.IntegrityError:
            print("AVISO: Esa traducción ya existe para este término.")


def ver_diccionario_completo():
    print("\n--- DICCIONARIO COMPLETO ---")
    with closing(conectar()) as conn:
        conceptos = conn.execute(
            "SELECT id_concepto, area, termino_es, definicion_es "
            "FROM Conceptos_ES ORDER BY norm(termino_es), fold(termino_es)"
        ).fetchall()

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
        resultados = conn.execute(
            """
            SELECT DISTINCT c.id_concepto, c.area, c.termino_es, c.definicion_es
            FROM Conceptos_ES c
            LEFT JOIN Traducciones t ON t.id_concepto = c.id_concepto
            WHERE instr(norm(c.termino_es), norm(:q)) > 0
               OR instr(norm(c.definicion_es), norm(:q)) > 0
               OR instr(norm(c.area), norm(:q)) > 0
               OR instr(norm(t.termino_traducido), norm(:q)) > 0
            ORDER BY norm(c.termino_es), fold(c.termino_es)
            """,
            {"q": texto},
        ).fetchall()

        if not resultados:
            print(f"Sin resultados para '{texto}'.")
            return
        print(f"\n{len(resultados)} resultado(s) para '{texto}':")
        for c in resultados:
            mostrar_concepto(conn, c)


def editar_concepto():
    print("\n--- 5. Editar un término ---")
    with closing(conectar()) as conn, conn:
        concepto = pedir_concepto_existente(conn, "¿Qué término en ESPAÑOL quieres editar?: ")
        if concepto is None:
            return

        print("Pulsa Enter para dejar un campo como está. "
              "En la definición, escribe '-' para vaciarla.")
        area = pedir_con_valor_actual("Área", concepto["area"])
        termino = pedir_con_valor_actual("Término", concepto["termino_es"])
        definicion = pedir_con_valor_actual("Definición", concepto["definicion_es"] or "")
        if definicion == "-":
            definicion = ""

        # ¿El nuevo nombre choca con OTRO concepto distinto de este?
        otro = buscar_concepto_por_termino(conn, termino)
        if otro and otro["id_concepto"] != concepto["id_concepto"]:
            print("AVISO: Ya existe otro término con ese nombre. No se ha cambiado nada.")
            return

        conn.execute(
            "UPDATE Conceptos_ES SET area = ?, termino_es = ?, definicion_es = ? "
            "WHERE id_concepto = ?",
            (area, termino, definicion, concepto["id_concepto"]),
        )
        print("✅ Término actualizado.")


def gestionar_traducciones():
    print("\n--- 6. Editar o borrar una traducción ---")
    with closing(conectar()) as conn, conn:
        concepto = pedir_concepto_existente(conn, "¿De qué término en ESPAÑOL?: ")
        if concepto is None:
            return

        traducciones = obtener_traducciones(conn, concepto["id_concepto"])
        if not traducciones:
            print("Este término todavía no tiene traducciones.")
            return

        print(f"\nTraducciones de '{concepto['termino_es']}':")
        for i, t in enumerate(traducciones, start=1):
            print(f"  {i}. {t['idioma']}: {t['termino_traducido']}")

        n = pedir_numero("¿Cuál? (número, Enter para cancelar): ", len(traducciones))
        if n is None:
            print("Cancelado.")
            return
        elegida = traducciones[n - 1]

        accion = input("¿Editar (e) o borrar (b)?: ").strip().lower()
        if accion == "b":
            if pedir_confirmacion(f"¿Borrar '{elegida['termino_traducido']}' ({elegida['idioma']})?"):
                conn.execute("DELETE FROM Traducciones WHERE id_traduccion = ?",
                             (elegida["id_traduccion"],))
                print("🗑️  Traducción borrada.")
            else:
                print("Cancelado.")
        elif accion == "e":
            idioma = pedir_con_valor_actual("Idioma", elegida["idioma"]).upper()
            if not (idioma.isalpha() and 2 <= len(idioma) <= 3):
                print("⚠️  Código de idioma no válido. No se ha cambiado nada.")
                return
            texto = pedir_con_valor_actual("Término traducido", elegida["termino_traducido"])
            try:
                conn.execute(
                    "UPDATE Traducciones SET idioma = ?, termino_traducido = ? "
                    "WHERE id_traduccion = ?",
                    (idioma, texto, elegida["id_traduccion"]),
                )
                print("✅ Traducción actualizada.")
            except sqlite3.IntegrityError:
                print("AVISO: Ya existe esa traducción para este término. No se ha cambiado nada.")
        else:
            print("Cancelado.")


def borrar_concepto():
    print("\n--- 7. Borrar un término ---")
    with closing(conectar()) as conn, conn:
        concepto = pedir_concepto_existente(conn, "¿Qué término en ESPAÑOL quieres borrar?: ")
        if concepto is None:
            return

        mostrar_concepto(conn, concepto)
        n = len(obtener_traducciones(conn, concepto["id_concepto"]))
        aviso = f" y sus {n} traducción(es)" if n else ""
        if not pedir_confirmacion(f"\n¿Seguro que quieres borrar '{concepto['termino_es']}'{aviso}? "
                                  "No se puede deshacer"):
            print("Cancelado.")
            return

        # Primero las traducciones (hijas) y luego el concepto (padre);
        # al estar en la misma transacción, o se borra todo o no se borra nada.
        conn.execute("DELETE FROM Traducciones WHERE id_concepto = ?", (concepto["id_concepto"],))
        conn.execute("DELETE FROM Conceptos_ES WHERE id_concepto = ?", (concepto["id_concepto"],))
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


if __name__ == "__main__":
    try:
        menu()
    except (KeyboardInterrupt, EOFError):
        print("\nHasta pronto 👋")