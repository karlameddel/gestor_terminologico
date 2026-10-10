import sqlite3
import unicodedata
from contextlib import closing
from datetime import datetime
from pathlib import Path

# La base de datos se guarda junto a este archivo, se ejecute desde donde se ejecute.
DB_PATH = Path(__file__).with_name("gestor_traductor.db")

# Idioma de origen. Cada concepto tiene exactamente un término en este idioma.
IDIOMA_ORIGEN = "ES"


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
    Se usa para buscar y ordenar sin preocuparse de las tildes."""
    descompuesto = unicodedata.normalize("NFD", _fold(texto))
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def conectar():
    conn = sqlite3.connect(DB_PATH)
    # SQLite no comprueba las claves foráneas si no se le pide explícitamente.
    conn.execute("PRAGMA foreign_keys = ON")
    # Permite acceder a las columnas por nombre: fila["termino"]
    conn.row_factory = sqlite3.Row
    conn.create_function("fold", 1, _fold, deterministic=True)
    conn.create_function("norm", 1, _norm, deterministic=True)
    return conn


def _crear_esquema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Conceptos (
            id_concepto INTEGER PRIMARY KEY AUTOINCREMENT,
            area        TEXT NOT NULL,
            definicion  TEXT NOT NULL DEFAULT ''
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Terminos (
            id_termino  INTEGER PRIMARY KEY AUTOINCREMENT,
            id_concepto INTEGER NOT NULL
                        REFERENCES Conceptos(id_concepto) ON DELETE CASCADE,
            idioma      TEXT NOT NULL,
            termino     TEXT NOT NULL,
            UNIQUE (id_concepto, idioma, termino)
        )""")
    # Regla: como mucho UN término en español por concepto.
    # (Si algún día hay más idiomas de origen, basta con borrar este índice.)
    conn.execute(f"""
        CREATE UNIQUE INDEX IF NOT EXISTS un_termino_origen_por_concepto
        ON Terminos (id_concepto) WHERE idioma = '{IDIOMA_ORIGEN}'""")


# ---------- Migración desde el formato antiguo (Conceptos_ES + Traducciones) ----------

def _tabla_existe(conn, nombre):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (nombre,)
    ).fetchone() is not None


def _hacer_copia_de_seguridad(conn):
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = DB_PATH.with_name(f"{DB_PATH.stem}_copia_{marca}.db")
    with closing(sqlite3.connect(destino)) as copia:
        conn.backup(copia)
    return destino


def migrar_esquema_antiguo(conn):
    """Pasa los datos de Conceptos_ES + Traducciones al esquema nuevo.
    Todo ocurre en UNA transacción: o se migra todo, o no se toca nada.
    Devuelve (conceptos, traducciones, descartadas)."""
    n_conceptos = conn.execute("SELECT COUNT(*) FROM Conceptos_ES").fetchone()[0]
    n_antiguas = conn.execute("SELECT COUNT(*) FROM Traducciones").fetchone()[0]
    # Traducciones válidas: sin repetidos, no marcadas como "ES" y con concepto existente.
    n_validas = conn.execute(
        """SELECT COUNT(*) FROM (
               SELECT DISTINCT id_concepto, UPPER(idioma), termino_traducido
               FROM Traducciones
               WHERE UPPER(idioma) <> ?
                 AND id_concepto IN (SELECT id_concepto FROM Conceptos_ES))""",
        (IDIOMA_ORIGEN,),
    ).fetchone()[0]

    conn.isolation_level = None  # nosotros controlamos la transacción a mano
    conn.execute("BEGIN")
    try:
        _crear_esquema(conn)
        # Se conservan los mismos id_concepto para no romper nada.
        conn.execute(
            """INSERT INTO Conceptos (id_concepto, area, definicion)
               SELECT id_concepto, COALESCE(area, ''), COALESCE(definicion_es, '')
               FROM Conceptos_ES""")
        conn.execute(
            "INSERT INTO Terminos (id_concepto, idioma, termino) "
            "SELECT id_concepto, ?, termino_es FROM Conceptos_ES",
            (IDIOMA_ORIGEN,),
        )
        conn.execute(
            """INSERT OR IGNORE INTO Terminos (id_concepto, idioma, termino)
               SELECT id_concepto, UPPER(idioma), termino_traducido
               FROM Traducciones
               WHERE UPPER(idioma) <> ?
                 AND id_concepto IN (SELECT id_concepto FROM Conceptos_ES)""",
            (IDIOMA_ORIGEN,),
        )

        # Comprobación de seguridad ANTES de borrar nada.
        c_nuevos = conn.execute("SELECT COUNT(*) FROM Conceptos").fetchone()[0]
        t_es = conn.execute("SELECT COUNT(*) FROM Terminos WHERE idioma = ?",
                            (IDIOMA_ORIGEN,)).fetchone()[0]
        t_otros = conn.execute("SELECT COUNT(*) FROM Terminos WHERE idioma <> ?",
                               (IDIOMA_ORIGEN,)).fetchone()[0]
        if (c_nuevos, t_es, t_otros) != (n_conceptos, n_conceptos, n_validas):
            raise RuntimeError("los recuentos no coinciden tras copiar los datos")

        conn.execute("DROP TABLE Traducciones")
        conn.execute("DROP TABLE Conceptos_ES")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.isolation_level = ""  # vuelve al modo normal

    return n_conceptos, n_validas, n_antiguas - n_validas


def inicializar_bd():
    with closing(conectar()) as conn:
        if _tabla_existe(conn, "Conceptos_ES"):
            print("🔄 Se ha detectado una base de datos con el formato antiguo. Actualizando...")
            copia = _hacer_copia_de_seguridad(conn)
            try:
                n_c, n_t, descartadas = migrar_esquema_antiguo(conn)
            except Exception as e:
                print(f"❌ No se pudo actualizar la base de datos: {e}")
                print(f"   Tus datos originales no se han modificado. Copia de seguridad: {copia.name}")
                raise SystemExit(1)
            print(f"✅ Migrados {n_c} término(s) y {n_t} traducción(es). "
                  f"Copia de seguridad: {copia.name}")
            if descartadas:
                print(f"   ({descartadas} traducción(es) repetidas o inválidas no se han copiado.)")
        with conn:
            _crear_esquema(conn)


# ---------- Utilidades de entrada ----------

def pedir_texto(mensaje, obligatorio=True):
    """Pide un texto por pantalla. Si es obligatorio, repite hasta que no esté vacío."""
    while True:
        valor = input(mensaje).strip()
        if valor or not obligatorio:
            return valor
        print("⚠️  Este campo no puede estar vacío.")


def validar_idioma(codigo):
    """Devuelve un mensaje de error si el código no vale para una traducción, o None si es válido."""
    if not (codigo.isalpha() and 2 <= len(codigo) <= 3):
        return "Escribe un código de 2 o 3 letras (ej. EN, FR, DE)."
    if codigo == IDIOMA_ORIGEN:
        return "El español es el idioma de origen; aquí se añaden traducciones a OTROS idiomas."
    return None


def pedir_idioma(mensaje="Idioma destino (ej. FR, EN): "):
    while True:
        codigo = input(mensaje).strip().upper()
        error = validar_idioma(codigo)
        if error is None:
            return codigo
        print(f"⚠️  {error}")


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

def conceptos_por_termino_es(conn, texto):
    """Todos los conceptos (significados) cuyo término en español es `texto`."""
    return conn.execute(
        """SELECT c.id_concepto, c.area, c.definicion, t.termino AS termino_es
           FROM Conceptos c
           JOIN Terminos t ON t.id_concepto = c.id_concepto AND t.idioma = ?
           WHERE fold(t.termino) = fold(?)
           ORDER BY fold(c.definicion), c.id_concepto""",
        (IDIOMA_ORIGEN, texto),
    ).fetchall()


def hay_significado_repetido(conn, termino, definicion, excluir_id=None):
    """¿Existe ya OTRO concepto con el mismo término en español y la misma definición?"""
    return conn.execute(
        """SELECT 1 FROM Conceptos c
           JOIN Terminos t ON t.id_concepto = c.id_concepto AND t.idioma = ?
           WHERE fold(t.termino) = fold(?) AND fold(c.definicion) = fold(?)
             AND c.id_concepto IS NOT ?""",
        (IDIOMA_ORIGEN, termino, definicion, excluir_id),
    ).fetchone() is not None


def descripcion_significado(c):
    return f"[{c['area']}] {c['definicion'] or 'sin definición'}"


def elegir_concepto(conn, mensaje):
    """Pide un término en español. Si tiene varios significados, deja elegir uno.
    Devuelve la fila del concepto o None."""
    texto = pedir_texto(mensaje)
    candidatos = conceptos_por_termino_es(conn, texto)
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


def obtener_traducciones(conn, id_concepto):
    return conn.execute(
        "SELECT id_termino, idioma, termino FROM Terminos "
        "WHERE id_concepto = ? AND idioma <> ? ORDER BY idioma, termino",
        (id_concepto, IDIOMA_ORIGEN),
    ).fetchall()


def mostrar_concepto(conn, c):
    definicion = c["definicion"] or "sin definición"
    print(f"\n [ES] {c['termino_es']} | CATEGORÍA: {c['area']} | DEFINICIÓN: '{definicion}'")
    for t in obtener_traducciones(conn, c["id_concepto"]):
        print(f"   ↳ {t['idioma']}: {t['termino']}")


# ---------- Opciones del menú ----------

def añadir_concepto_origen():
    print("\n--- 1. Nuevo Término (Origen: Español) ---")
    termino = pedir_texto("Término en Español: ")

    with closing(conectar()) as conn, conn:
        existentes = conceptos_por_termino_es(conn, termino)
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

        if hay_significado_repetido(conn, termino, definicion):
            print("AVISO: Ya existe ese término con esa misma definición. No se ha guardado.")
            return

        cur = conn.execute("INSERT INTO Conceptos (area, definicion) VALUES (?, ?)",
                           (area, definicion))
        conn.execute("INSERT INTO Terminos (id_concepto, idioma, termino) VALUES (?, ?, ?)",
                     (cur.lastrowid, IDIOMA_ORIGEN, termino))
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
            conn.execute(
                "INSERT INTO Terminos (id_concepto, idioma, termino) VALUES (?, ?, ?)",
                (concepto["id_concepto"], idioma, traduccion),
            )
            print(f"✅ Traducción guardada: {concepto['termino_es']} (ES) -> {traduccion} ({idioma})")
        except sqlite3.IntegrityError:
            print("AVISO: Esa traducción ya existe para este término.")


def ver_diccionario_completo():
    print("\n--- DICCIONARIO COMPLETO ---")
    with closing(conectar()) as conn:
        conceptos = conn.execute(
            """SELECT c.id_concepto, c.area, c.definicion, t.termino AS termino_es
               FROM Conceptos c
               JOIN Terminos t ON t.id_concepto = c.id_concepto AND t.idioma = ?
               ORDER BY norm(t.termino), fold(t.termino), fold(c.definicion), c.id_concepto""",
            (IDIOMA_ORIGEN,),
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
            """SELECT c.id_concepto, c.area, c.definicion, es.termino AS termino_es
               FROM Conceptos c
               JOIN Terminos es ON es.id_concepto = c.id_concepto AND es.idioma = :origen
               WHERE instr(norm(c.definicion), norm(:q)) > 0
                  OR instr(norm(c.area), norm(:q)) > 0
                  OR EXISTS (SELECT 1 FROM Terminos t
                             WHERE t.id_concepto = c.id_concepto
                               AND instr(norm(t.termino), norm(:q)) > 0)
               ORDER BY norm(es.termino), fold(es.termino), c.id_concepto""",
            {"q": texto, "origen": IDIOMA_ORIGEN},
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

        if hay_significado_repetido(conn, termino, definicion, concepto["id_concepto"]):
            print("AVISO: Ya existe otro concepto con ese término y esa definición. "
                  "No se ha cambiado nada.")
            return

        conn.execute("UPDATE Conceptos SET area = ?, definicion = ? WHERE id_concepto = ?",
                     (area, definicion, concepto["id_concepto"]))
        conn.execute("UPDATE Terminos SET termino = ? WHERE id_concepto = ? AND idioma = ?",
                     (termino, concepto["id_concepto"], IDIOMA_ORIGEN))
        print("✅ Término actualizado.")


def gestionar_traducciones():
    print("\n--- 6. Editar o borrar una traducción ---")
    with closing(conectar()) as conn, conn:
        concepto = elegir_concepto(conn, "¿De qué término en ESPAÑOL?: ")
        if concepto is None:
            return

        traducciones = obtener_traducciones(conn, concepto["id_concepto"])
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
                conn.execute("DELETE FROM Terminos WHERE id_termino = ?", (elegida["id_termino"],))
                print("🗑️  Traducción borrada.")
            else:
                print("Cancelado.")
        elif accion == "e":
            idioma = pedir_con_valor_actual("Idioma", elegida["idioma"]).upper()
            error = validar_idioma(idioma)
            if error:
                print(f"⚠️  {error} No se ha cambiado nada.")
                return
            texto = pedir_con_valor_actual("Término traducido", elegida["termino"])
            try:
                conn.execute("UPDATE Terminos SET idioma = ?, termino = ? WHERE id_termino = ?",
                             (idioma, texto, elegida["id_termino"]))
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
        n = len(obtener_traducciones(conn, concepto["id_concepto"]))
        aviso = f" y sus {n} traducción(es)" if n else ""
        if not pedir_confirmacion(f"\n¿Seguro que quieres borrar este significado de "
                                  f"'{concepto['termino_es']}'{aviso}? No se puede deshacer"):
            print("Cancelado.")
            return

        # ON DELETE CASCADE: al borrar el concepto, la base de datos borra
        # automáticamente todos sus términos (ES y traducciones).
        conn.execute("DELETE FROM Conceptos WHERE id_concepto = ?", (concepto["id_concepto"],))
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