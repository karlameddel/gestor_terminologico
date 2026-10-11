"""Conexión, creación del esquema y migración desde el formato antiguo.

El esquema (tablas Conceptos y Terminos) está explicado con un dibujo
en el README, en la sección "Estructura de la Base de Datos".
"""
import sqlite3
from contextlib import closing
from datetime import datetime

from . import config, texto


def conectar():
    conn = sqlite3.connect(config.DB_PATH)
    # SQLite no comprueba las claves foráneas si no se le pide explícitamente.
    conn.execute("PRAGMA foreign_keys = ON")
    # Permite acceder a las columnas por nombre: fila["termino"]
    conn.row_factory = sqlite3.Row
    conn.create_function("fold", 1, texto.fold, deterministic=True)
    conn.create_function("norm", 1, texto.norm, deterministic=True)
    return conn


def crear_esquema(conn):
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
        ON Terminos (id_concepto) WHERE idioma = '{config.IDIOMA_ORIGEN}'""")


# ---------- Migración desde el formato antiguo (Conceptos_ES + Traducciones) ----------

def _tabla_existe(conn, nombre):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (nombre,)
    ).fetchone() is not None


def _hacer_copia_de_seguridad(conn):
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = config.DB_PATH.with_name(f"{config.DB_PATH.stem}_copia_{marca}.db")
    with closing(sqlite3.connect(destino)) as copia:
        conn.backup(copia)
    return destino


def migrar_esquema_antiguo(conn):
    """Pasa los datos de Conceptos_ES + Traducciones al esquema nuevo.
    Todo ocurre en UNA transacción: o se migra todo, o no se toca nada.
    Devuelve (conceptos, traducciones, descartadas)."""
    origen = config.IDIOMA_ORIGEN
    n_conceptos = conn.execute("SELECT COUNT(*) FROM Conceptos_ES").fetchone()[0]
    n_antiguas = conn.execute("SELECT COUNT(*) FROM Traducciones").fetchone()[0]
    # Traducciones válidas: sin repetidos, no marcadas como "ES" y con concepto existente.
    n_validas = conn.execute(
        """SELECT COUNT(*) FROM (
               SELECT DISTINCT id_concepto, UPPER(idioma), termino_traducido
               FROM Traducciones
               WHERE UPPER(idioma) <> ?
                 AND id_concepto IN (SELECT id_concepto FROM Conceptos_ES))""",
        (origen,),
    ).fetchone()[0]

    conn.isolation_level = None  # nosotros controlamos la transacción a mano
    conn.execute("BEGIN")
    try:
        crear_esquema(conn)
        # Se conservan los mismos id_concepto para no romper nada.
        conn.execute(
            """INSERT INTO Conceptos (id_concepto, area, definicion)
               SELECT id_concepto, COALESCE(area, ''), COALESCE(definicion_es, '')
               FROM Conceptos_ES""")
        conn.execute(
            "INSERT INTO Terminos (id_concepto, idioma, termino) "
            "SELECT id_concepto, ?, termino_es FROM Conceptos_ES",
            (origen,),
        )
        conn.execute(
            """INSERT OR IGNORE INTO Terminos (id_concepto, idioma, termino)
               SELECT id_concepto, UPPER(idioma), termino_traducido
               FROM Traducciones
               WHERE UPPER(idioma) <> ?
                 AND id_concepto IN (SELECT id_concepto FROM Conceptos_ES)""",
            (origen,),
        )

        # Comprobación de seguridad ANTES de borrar nada.
        c_nuevos = conn.execute("SELECT COUNT(*) FROM Conceptos").fetchone()[0]
        t_es = conn.execute("SELECT COUNT(*) FROM Terminos WHERE idioma = ?",
                            (origen,)).fetchone()[0]
        t_otros = conn.execute("SELECT COUNT(*) FROM Terminos WHERE idioma <> ?",
                               (origen,)).fetchone()[0]
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
            crear_esquema(conn)