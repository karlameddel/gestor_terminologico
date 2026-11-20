"""Gestor terminológico en el navegador. Este es el archivo que se empaqueta como .exe.

Ejecútalo con:  python app_web.py
Arranca un servidor local (solo accesible desde este ordenador) y abre el navegador.
"""
import threading
import webbrowser

from gestor import basedatos, config
from gestor.web_servidor import crear_servidor

PUERTO_PREFERIDO = 8765


def main():
    try:
        resultado = basedatos.inicializar_bd()
    except basedatos.MigracionError as e:
        print(f"❌ No se pudo actualizar la base de datos: {e}")
        print(f"   Tus datos originales no se han modificado. Copia de seguridad: {e.copia.name}")
        input("Pulsa Enter para cerrar...")
        return 1
    if resultado:
        print(f"✅ Base de datos antigua migrada: {resultado.conceptos} término(s) y "
              f"{resultado.traducciones} traducción(es). Copia de seguridad: {resultado.copia.name}")

    try:
        servidor = crear_servidor(puerto=PUERTO_PREFERIDO)
    except OSError:                       # puerto ocupado (otra copia abierta): usa uno libre
        servidor = crear_servidor(puerto=0)
    url = f"http://127.0.0.1:{servidor.server_address[1]}/"

    print("=" * 62)
    print("  GESTOR TERMINOLÓGICO está abierto en tu navegador.")
    print(f"  Si no se ha abierto solo, copia esto en el navegador: {url}")
    print(f"  Tus datos se guardan en: {config.DB_PATH}")
    print("  Para cerrarlo: botón «Cerrar programa» de la página, o cierra esta ventana.")
    print("=" * 62)

    threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())