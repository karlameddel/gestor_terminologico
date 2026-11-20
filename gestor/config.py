import sys
from pathlib import Path


def carpeta_de_datos(congelado=None, ejecutable=None):
    """Carpeta donde se guarda la base de datos.

    - Ejecutado con Python: la carpeta raíz del proyecto (junto a main.py).
    - Empaquetado como .exe (PyInstaller): junto al .exe. Aquí NO vale __file__:
      con la opción de un solo archivo apunta a una carpeta temporal que se borra
      al cerrar el programa, y se perderían todos los datos.
    """
    if congelado is None:
        congelado = getattr(sys, "frozen", False)
    if ejecutable is None:
        ejecutable = sys.executable
    if congelado:
        return Path(ejecutable).resolve().parent
    return Path(__file__).resolve().parent.parent


DB_PATH = carpeta_de_datos() / "gestor_traductor.db"

# Idioma de origen. Cada concepto tiene exactamente un término en este idioma.
IDIOMA_ORIGEN = "ES"