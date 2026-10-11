from pathlib import Path

# La base de datos se guarda en la carpeta raíz del proyecto (junto a main.py),
# se ejecute desde donde se ejecute.
DB_PATH = Path(__file__).resolve().parent.parent / "gestor_traductor.db"

# Idioma de origen. Cada concepto tiene exactamente un término en este idioma.
IDIOMA_ORIGEN = "ES"