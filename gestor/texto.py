"""Comparación de textos que respeta tildes y mayúsculas de cualquier idioma.

SQLite solo ignora mayúsculas en letras ASCII (COLLATE NOCASE y LIKE no
distinguen "a" de "A", pero SÍ distinguen "á" de "Á" o "ñ" de "Ñ").
Para un gestor en varios idiomas necesitamos algo mejor, así que
`basedatos.conectar()` le enseña a SQLite estas dos funciones.
"""
import unicodedata


def fold(texto):
    """Minúsculas 'inteligentes' (Árbol == árbol, Straße == strasse)."""
    return (texto or "").casefold()


def norm(texto):
    """Como fold, y además sin tildes ni diéresis: 'Informática' -> 'informatica'.
    Se usa para buscar y ordenar sin preocuparse de las tildes."""
    descompuesto = unicodedata.normalize("NFD", fold(texto))
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")