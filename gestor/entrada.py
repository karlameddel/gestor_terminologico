"""Funciones genéricas para pedir datos por teclado."""


def pedir_texto(mensaje, obligatorio=True):
    """Pide un texto por pantalla. Si es obligatorio, repite hasta que no esté vacío."""
    while True:
        valor = input(mensaje).strip()
        if valor or not obligatorio:
            return valor
        print("⚠️  Este campo no puede estar vacío.")


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