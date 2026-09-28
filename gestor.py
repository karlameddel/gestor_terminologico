import sqlite3

def conectar():
    return sqlite3.connect('gestor_traductor.db')

def inicializar_bd():
    conn = conectar()
    cursor = conn.cursor()
    # TABLA 1: El idioma origen (Español como base)
    cursor.execute('''CREATE TABLE IF NOT EXISTS Conceptos_ES 
                      (id_concepto INTEGER PRIMARY KEY AUTOINCREMENT, 
                       area TEXT, 
                       termino_es TEXT UNIQUE, 
                       definicion_es TEXT)''')
    
    # TABLA 2: Las traducciones conectadas al término en español
    cursor.execute('''CREATE TABLE IF NOT EXISTS Traducciones 
                      (id_traduccion INTEGER PRIMARY KEY AUTOINCREMENT, 
                       id_concepto INTEGER, 
                       idioma TEXT, 
                       termino_traducido TEXT,
                       FOREIGN KEY (id_concepto) REFERENCES Conceptos_ES(id_concepto))''')
    conn.commit()
    conn.close()

def añadir_concepto_origen():
    print("\n--- 1. Nuevo Término (Origen: Español) ---")
    area = input("Área (ej. Comida): ").capitalize()
    termino = input("Término en Español: ").strip().lower()
    definicion = input("Definición: ")
    
    conn = conectar(); cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Conceptos_ES (area, termino_es, definicion_es) VALUES (?, ?, ?)", 
                       (area, termino, definicion))
        conn.commit()
        print(f"✅ Concepto '{termino}' creado correctamente.")
    except sqlite3.IntegrityError:
        print("AVISO: Ese término en español ya existe en la base de datos.")
    conn.close()

def añadir_traduccion():
    print("\n--- 2. Añadir Traducción ---")
    busqueda = input("¿De qué término en ESPAÑOL quieres añadir la traducción?: ").strip().lower()
    
    conn = conectar(); cursor = conn.cursor()
    cursor.execute("SELECT id_concepto FROM Conceptos_ES WHERE termino_es = ?", (busqueda,))
    resultado = cursor.fetchone()
    
    if resultado:
        id_c = resultado[0]
        idioma = input("Idioma destino (ej. FR, EN): ").upper()
        traduccion = input("Término traducido: ").strip()
        
        cursor.execute("INSERT INTO Traducciones (id_concepto, idioma, termino_traducido) VALUES (?, ?, ?)", 
                       (id_c, idioma, traduccion))
        conn.commit()
        print(f"Traducción guardada: {busqueda} (ES) -> {traduccion} ({idioma})")
    else:
        print("No existe ese término en español. Créalo primero en la opción 1.")
    conn.close()

def ver_diccionario_completo():
    conn = conectar(); cursor = conn.cursor()
    print("\n--- DICCIONARIO COMPLETO ---")
    # Seleccionamos el origen
    cursor.execute("SELECT id_concepto, area, termino_es, definicion_es FROM Conceptos_ES")
    conceptos = cursor.fetchall()
    
    for c in conceptos:
        print(f"\n [ES] {c[2]} | CATEGORÍA: {c[1]} | DEFINICIÓN: '{c[3]}'")
        # Buscamos sus traducciones
        cursor.execute("SELECT idioma, termino_traducido FROM Traducciones WHERE id_concepto = ?", (c[0],))
        traducciones = cursor.fetchall()
        for t in traducciones:
            print(f"   ↳ {t[0]}: {t[1]}")
    conn.close()

def menu():
    inicializar_bd()
    while True:
        print("\n=== GESTOR TERMINOLÓGICO (Modelo Origen-Destino) ===")
        print("1. Añadir nuevo término en español (Origen)")
        print("2. Añadir Traducción a un término existente")
        print("3. Ver diccionario completo")
        print("4. Salir")
        
        op = input("Selecciona: ")
        if op == "1": añadir_concepto_origen()
        elif op == "2": añadir_traduccion()
        elif op == "3": ver_diccionario_completo()
        elif op == "4": break

if __name__ == "__main__":
    menu()
