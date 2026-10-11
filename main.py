"""Punto de entrada. Ejecuta el programa con:  python main.py"""
from gestor.menu import menu

if __name__ == "__main__":
    try:
        menu()
    except (KeyboardInterrupt, EOFError):
        print("\nHasta pronto 👋")