# 📚 Gestor Terminológico

¡Bienvenido/a a mi repositorio!

Esta herramienta nace gracias a la colaboración con una [compañera estudiante de **Traducción e Interpretación**](https://github.com/Yaddygd06). Ella aporta la visión experta, identifica las necesidades reales del sector y define la lógica conceptual que requiere un traductor profesional. Mi labor consiste en tomar todas esas ideas, diseñar la arquitectura de la base de datos y escribir el código para convertirlas en una aplicación funcional.

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
- **Importar** glosarios desde CSV y **exportar** el diccionario, para trabajar con Excel o Google Sheets.

## Cómo ejecutarlo
Solo necesitas Python 3 (SQLite ya viene incluido, no hay que instalar nada más):

```bash
git clone https://github.com/<tu-usuario>/gestor_terminologico.git
cd gestor_terminologico
python app_web.py      # interfaz en el navegador (la recomendada)
python main.py         # versión de menú en la terminal
```

Las dos usan **la misma base de datos**, así que se pueden alternar. La primera vez se crea automáticamente el archivo `gestor_traductor.db` junto a `main.py`. Ese archivo contiene tus datos y no se sube a GitHub.

## Interfaz en el navegador
`python app_web.py` arranca un pequeño servidor **solo accesible desde tu propio ordenador** y abre el navegador. No hay que instalar nada: usa solo la biblioteca estándar de Python.

- **Diccionario** con buscador (sin tildes ni mayúsculas), y formulario para añadir términos. Si el término ya existe, hay que marcar que es otro significado y poner su definición.
- **Página de cada término:** editar su área y definición, y añadir, editar o borrar traducciones.
- **Importar CSV:** se elige el archivo, se muestra un resumen (nuevos, ampliados, errores con su fila) y solo se guarda al confirmar.
- **Exportar CSV:** descarga el glosario para abrirlo en Excel o Google Sheets.
- **Cerrar programa:** apaga el servidor.

Protecciones: solo escucha en `127.0.0.1`, rechaza peticiones que lleguen desde otras páginas web abiertas en el navegador y nunca interpreta como HTML lo que se escribe en el glosario.

## Crear el programa para Windows (.exe)
Para que alguien sin Python pueda usar el gestor con doble clic, se empaqueta `app_web.py` con PyInstaller. Un `.exe` solo se puede construir **en Windows**. Hay dos formas:

**A) Con GitHub (sin instalar nada):** en la pestaña *Actions* del repositorio, elige *Construir .exe* y pulsa *Run workflow*. Al terminar, descarga `GestorTerminologico-windows` de la sección *Artifacts*. Si en vez de eso creas una etiqueta que empiece por `v` (por ejemplo `v1.0`), el `.exe` se publica además en *Releases*.

**B) En tu ordenador:** instala el Python oficial de [python.org](https://www.python.org/downloads/) (marca *Add python.exe to PATH*; el Python de MSYS2 da problemas con PyInstaller) y ejecuta `construir_exe.bat`. El resultado queda en `dist\GestorTerminologico.exe`.

Al abrir el `.exe` aparece una ventana negra de consola (no la cierres mientras lo uses) y se abre el navegador. **La base de datos `gestor_traductor.db` se crea junto al `.exe`**: para hacer copia de seguridad, o para pasar los datos a otro ordenador, basta con copiar ese archivo.

Windows puede mostrar un aviso («Windows protegió su PC») porque el programa no está firmado digitalmente. Es normal en programas pequeños: *Más información → Ejecutar de todas formas*. Algunos antivirus también marcan por error los `.exe` hechos con PyInstaller.

## Importar y exportar (Excel / Google Sheets)
Las opciones **8** y **9** del menú trabajan con archivos CSV, que se abren y se guardan desde Excel y Google Sheets.

**Formato:** una fila por concepto y una columna por idioma.

```text
Área;Definición;ES;EN;FR
Informática;Placa principal de un ordenador;placa base;motherboard | mainboard;carte mère
```

- Las columnas son `Área`, `Definición` (opcional), `ES` y un código de idioma de 2-3 letras por cada idioma (`EN`, `FR`, `DE`...). Da igual el orden, las mayúsculas y las tildes. Cualquier otra columna se ignora.
- Varias traducciones en una misma celda se separan con ` | ` (por eso un término no puede contener el carácter `|`).
- **Varios significados:** dos filas con el mismo término en español y distinta definición son dos conceptos. Si una fila no trae definición y el término ya existe con un único significado, sus traducciones se añaden a ese. Si tiene varios, la fila se rechaza para no adivinar.
- Lo que ya existe no se duplica: importar dos veces el mismo archivo no cambia nada.
- Antes de guardar se muestra un resumen (nuevos, ampliados, errores con su número de fila) y hay que confirmar. Las filas con errores se saltan y el resto se importa.
- Se puede indicar un área por defecto para las filas que no la tengan.

**Excel:** al exportar se genera un CSV con `;` y UTF-8 (BOM), que Excel en español abre con doble clic. Si aparece todo en una columna: *Datos → Obtener datos → Desde texto/CSV* y elegir el punto y coma como delimitador. Para guardar un CSV desde Excel usa *CSV UTF-8*.

**Google Sheets:** *Archivo → Importar → Subir*, y para sacar un CSV *Archivo → Descargar → Valores separados por comas (.csv)*. Al importar, el programa detecta solo el separador (`;`, `,` o tabulador) y la codificación.

En la carpeta `ejemplos/` hay un archivo de prueba (`glosario_ejemplo.csv`), con un término de dos significados (*banco*) incluido.

## Estructura del proyecto
```text
main.py                  # punto de entrada: versión de menú en la terminal
app_web.py               # punto de entrada: interfaz en el navegador (es lo que se empaqueta)
construir_exe.bat        # construye el .exe en Windows
.github/workflows/       # tests y construcción del .exe automáticos en GitHub
ejemplos/
└── glosario_ejemplo.csv # archivo de prueba para importar
gestor/
├── config.py            # ruta de la base de datos e idioma de origen
├── texto.py             # comparar textos sin distinguir mayúsculas ni tildes
├── basedatos.py         # conexión, creación de tablas y migración
├── repositorio.py       # operaciones sobre los datos (solo SQL)
├── intercambio.py       # importar y exportar CSV (Excel / Google Sheets)
├── entrada.py           # pedir datos por teclado
├── menu.py              # menú y pantallas de la terminal
├── web_servidor.py      # servidor local: rutas, seguridad y acciones de la web
└── web_vistas.py        # pantallas HTML de la web
tests/                   # pruebas automáticas (ver más abajo)
```
El código está separado en capas: `menu.py` y `web_servidor.py` se encargan de lo que se ve y se pregunta, y `repositorio.py` e `intercambio.py` de leer y guardar datos. Por eso la terminal y el navegador comparten la misma lógica: se puede cambiar la interfaz o añadir funciones sin tocar el resto.

## Tests
El proyecto tiene pruebas automáticas que comprueban que todo sigue funcionando después de cada cambio: búsqueda, varios significados, migración de bases de datos antiguas, importación y exportación, y el menú completo.

```bash
python -m unittest          # ejecuta todas
python -m unittest -v       # igual, mostrando el nombre de cada prueba
```

No hay que instalar nada (`unittest` viene con Python). Cada prueba trabaja con una base de datos temporal, así que **nunca toca tu `gestor_traductor.db`**. Si ves `OK` al final, todo va bien. Si ves `FAILED`, indica qué prueba falló y por qué.

| Archivo | Qué comprueba |
|---|---|
| `test_texto.py` | Comparar textos sin distinguir mayúsculas ni tildes |
| `test_repositorio.py` | Conceptos, traducciones, significados repetidos, búsqueda y reglas de la base de datos |
| `test_basedatos.py` | Creación de tablas y migración (incluido qué pasa si falla) |
| `test_intercambio.py` | Importar y exportar CSV, formatos de Excel y Google Sheets, errores |
| `test_menu.py` | Sesiones completas simulando a una persona usando el menú |
| `test_web.py` | La interfaz web con un servidor de verdad: páginas, formularios, importar/exportar y seguridad |
| `test_config.py` | Dónde se guarda la base de datos (también cuando es un `.exe`) |

Cuando añadas una función nueva, añade también su prueba. Y si encuentras un fallo, escribe primero la prueba que lo reproduce y luego arréglalo: así no vuelve a aparecer.

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