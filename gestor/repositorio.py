"""Operaciones sobre los datos: solo SQL, sin input() ni print().

Todas las funciones reciben la conexión (`conn`) y NO hacen commit: de eso
se encarga quien las llama (con `with conn:`), así puede agrupar varias
operaciones en una sola transacción. Al no depender del menú, las puede
usar también una futura importación de CSV o los tests.
"""
from .config import IDIOMA_ORIGEN


def validar_idioma(codigo):
    """Devuelve un mensaje de error si el código no vale para una traducción, o None si es válido.
    No distingue mayúsculas: 'es' y 'ES' son el mismo idioma."""
    codigo = codigo.strip().upper()
    if not (codigo.isalpha() and 2 <= len(codigo) <= 3):
        return "Escribe un código de 2 o 3 letras (ej. EN, FR, DE)."
    if codigo == IDIOMA_ORIGEN:
        return "El español es el idioma de origen; aquí se añaden traducciones a OTROS idiomas."
    return None


# ---------- Consultas ----------

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


def listar_conceptos(conn):
    """Todos los conceptos, ordenados alfabéticamente por su término en español."""
    return conn.execute(
        """SELECT c.id_concepto, c.area, c.definicion, t.termino AS termino_es
           FROM Conceptos c
           JOIN Terminos t ON t.id_concepto = c.id_concepto AND t.idioma = ?
           ORDER BY norm(t.termino), fold(t.termino), fold(c.definicion), c.id_concepto""",
        (IDIOMA_ORIGEN,),
    ).fetchall()


def buscar_conceptos(conn, texto):
    """Conceptos que contienen `texto` en su término, traducciones, definición o área.
    No distingue mayúsculas ni tildes, y admite palabras parciales."""
    return conn.execute(
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


def obtener_traducciones(conn, id_concepto):
    return conn.execute(
        "SELECT id_termino, idioma, termino FROM Terminos "
        "WHERE id_concepto = ? AND idioma <> ? ORDER BY idioma, termino",
        (id_concepto, IDIOMA_ORIGEN),
    ).fetchall()


# ---------- Altas, cambios y bajas ----------

def crear_concepto(conn, area, termino_es, definicion=""):
    """Crea un concepto con su término en español. Devuelve el id del concepto."""
    cur = conn.execute("INSERT INTO Conceptos (area, definicion) VALUES (?, ?)",
                       (area, definicion))
    conn.execute("INSERT INTO Terminos (id_concepto, idioma, termino) VALUES (?, ?, ?)",
                 (cur.lastrowid, IDIOMA_ORIGEN, termino_es))
    return cur.lastrowid


def crear_traduccion(conn, id_concepto, idioma, termino):
    """Añade una traducción (el código de idioma se guarda en mayúsculas).
    Lanza ValueError si el idioma no vale y sqlite3.IntegrityError si esa traducción ya existe."""
    error = validar_idioma(idioma)
    if error:
        raise ValueError(error)
    conn.execute("INSERT INTO Terminos (id_concepto, idioma, termino) VALUES (?, ?, ?)",
                 (id_concepto, idioma.strip().upper(), termino))


def actualizar_concepto(conn, id_concepto, area, termino_es, definicion):
    conn.execute("UPDATE Conceptos SET area = ?, definicion = ? WHERE id_concepto = ?",
                 (area, definicion, id_concepto))
    conn.execute("UPDATE Terminos SET termino = ? WHERE id_concepto = ? AND idioma = ?",
                 (termino_es, id_concepto, IDIOMA_ORIGEN))


def actualizar_traduccion(conn, id_termino, idioma, termino):
    """Lanza ValueError si el idioma no vale y sqlite3.IntegrityError si ya existe."""
    error = validar_idioma(idioma)
    if error:
        raise ValueError(error)
    conn.execute("UPDATE Terminos SET idioma = ?, termino = ? WHERE id_termino = ?",
                 (idioma.strip().upper(), termino, id_termino))


def borrar_traduccion(conn, id_termino):
    conn.execute("DELETE FROM Terminos WHERE id_termino = ?", (id_termino,))


def borrar_concepto(conn, id_concepto):
    # ON DELETE CASCADE: al borrar el concepto, la base de datos borra
    # automáticamente todos sus términos (ES y traducciones).
    conn.execute("DELETE FROM Conceptos WHERE id_concepto = ?", (id_concepto,))