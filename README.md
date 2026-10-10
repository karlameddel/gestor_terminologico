# 📚 Gestor Terminológico

¡Bienvenido/a a mi repositorio!

Esta herramienta nace gracias a la colaboración con una compañera estudiante de **Traducción e Interpretación**. Ella aporta la visión experta, identifica las necesidades reales del sector y define la lógica conceptual que requiere un traductor profesional. Mi labor consiste en tomar todas esas ideas, diseñar la arquitectura de la base de datos y escribir el código para convertirlas en una aplicación funcional.

Por ahora estás observando una primera versión ya que sigue on-going.

El objetivo final es construir una solución a medida que una el rigor de los datos con la precisión lingüística.

## Funcionamiento
A diferencia de un diccionario tradicional que solo da equivalencias de palabras, un gestor terminológico se centra en **conceptos**. Para un traductor, esta herramienta es vital porque permite:
* **Mantener la coherencia:** Asegura que un mismo término técnico (ej. *motherboard*) se traduzca siempre igual (ej. *placa base*) a lo largo de un proyecto enorme.
* **Aportar contexto:** Guarda no solo la traducción, sino la definición, el cliente, el área de especialidad médica/jurídica/técnica, y ejemplos de uso real.
* **Ahorrar tiempo:** Evita tener que documentarse e investigar la misma palabra compleja varias veces.

## Objetivo
Queremos crear una base de datos estructurada donde cada entrada sea un concepto que contenga la información de un término, el idioma, la definición del mismo.

## Tecnología
* **Lenguaje:** Python 3
* **Base de Datos:** SQLite (SQL relacional)
* **Control de versiones:** Git / GitHub

## Funciones disponibles
- Añadir términos en español con su área y definición, incluidos **términos con varios significados**.
- Añadir varias traducciones por término e idioma.
- Ver el diccionario completo, ordenado alfabéticamente.
- **Buscar** en términos, definiciones, áreas y traducciones (sin importar mayúsculas ni tildes, y con palabras parciales).
- **Editar** términos y traducciones, y **borrar** con confirmación previa.

## Cómo ejecutarlo
Solo necesitas Python 3 (SQLite ya viene incluido, no hay que instalar nada más):

```bash
git clone https://github.com/<tu-usuario>/gestor_terminologico.git
cd gestor_terminologico
python main.py
```

La primera vez se crea automáticamente el archivo `gestor_traductor.db` junto a `main.py`. Ese archivo contiene tus datos y no se sube a GitHub.

## Estructura del proyecto
```text
main.py                  # punto de entrada
gestor/
├── config.py            # ruta de la base de datos e idioma de origen
├── texto.py             # comparar textos sin distinguir mayúsculas ni tildes
├── basedatos.py         # conexión, creación de tablas y migración
├── repositorio.py       # operaciones sobre los datos (solo SQL)
├── entrada.py           # pedir datos por teclado
└── menu.py              # menú y pantallas
```
El código está separado en capas: `menu.py` se encarga de lo que se ve y se pregunta, y `repositorio.py` de leer y guardar datos. Así se puede cambiar la interfaz (por ejemplo, a una web) o añadir funciones nuevas (importar CSV) sin tocar el resto.

## Estructura de la Base de Datos
El modelo gira en torno al **concepto** (un significado concreto), no a la palabra. Dos tablas vinculadas:

```text
  Conceptos                        Terminos
┌─────────────┐  1          N  ┌─────────────┐
│ id_concepto │────────────────│ id_concepto │
│ area        │                │ idioma      │  ES, EN, FR...
│ definicion  │                │ termino     │
└─────────────┘                └─────────────┘
```

Un concepto = un significado. Su término en español y sus traducciones son filas de `Terminos`.

### 1. Tabla `Conceptos`
Cada fila es un significado único.
- **`id_concepto`:** identificador autoincremental.
- **`area`:** categoría temática (ej. Medicina, Informática, Legal).
- **`definicion`:** definición del concepto.

### 2. Tabla `Terminos`
Guarda las palabras de cada concepto, en cualquier idioma.
- **`id_concepto`:** vínculo (FK) con el concepto. Si se borra el concepto, se borran sus términos.
- **`idioma`:** código del idioma (`ES`, `EN`, `FR`...).
- **`termino`:** la palabra en ese idioma.

Cada concepto tiene **un término en español** (el idioma de origen) y tantas traducciones como se quiera.

### Varios significados
Como el término vive en `Terminos` y no en `Conceptos`, una misma palabra puede tener varios significados:

| Concepto | Área | Definición | ES | EN |
|---|---|---|---|---|
| 1 | Mobiliario | Asiento largo para varias personas | banco | bench |
| 2 | Finanzas | Entidad que gestiona dinero | banco | bank |

Al añadir un término que ya existe, el programa pregunta si es un significado nuevo y pide una definición para poder distinguirlos.

### Preparado para el futuro
El español es "solo un idioma más" en la tabla `Terminos`. Para permitir otros idiomas de origen bastará con quitar una restricción (el índice `un_termino_origen_por_concepto`), sin rehacer la base de datos.

### Bases de datos antiguas
Si abres el programa con una base de datos del formato anterior (`Conceptos_ES` + `Traducciones`), se **migra automáticamente** y antes se guarda una copia de seguridad (`gestor_traductor_copia_<fecha>.db`).

---
*Proyecto simplificado creado para aprender y practicar programación y gestión terminológica.*