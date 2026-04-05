# GESTOR TERMINOLÓGICO

¡Bienvenido/a a nuestro repositorio! Somos dos estudiantes universitarias y **este es nuestro primer proyecto de programación** juntas. Lo estamos desarrollando paso a paso con el objetivo de aprender, equivocarnos y, sobre todo, crear una herramienta útil que una nuestros dos mundos: la **Ciencia de Datos** y la **Traducción e Interpretación**.

## Funcionamiento
A diferencia de un diccionario tradicional que solo da equivalencias de palabras, un gestor terminológico se centra en **conceptos**. Para un traductor, esta herramienta es vital porque permite:
* **Mantener la coherencia:** Asegura que un mismo término técnico (ej. *motherboard*) se traduzca siempre igual (ej. *placa base*) a lo largo de un proyecto enorme.
* **Aportar contexto:** Guarda no solo la traducción, sino la definición, el cliente, el área de especialidad médica/jurídica/técnica, y ejemplos de uso real.
* **Ahorrar tiempo:** Evita tener que documentarse e investigar la misma palabra compleja varias veces.

## Objetivo
Queremos crear una base de datos estructurada donde cada entrada sea un concepto que contenga la información de un término, el idioma, la definición del mismo.

## Tecnologías
* **Lenguaje:** Python
* **Almacenamiento:** Archivos JSON (Fase 1)
* **Control de versiones:** Git / GitHub

## Roadmap
Construiremos este proyecto de forma gradual:

- [ ] **Fase 1 (Actual):** Script básico en Python para guardar términos por consola en un archivo `.json`.
- [ ] **Fase 2:** Añadir funciones de búsqueda para consultar términos guardados.
- [ ] **Fase 3:** Implementar edición y borrado de términos (CRUD completo).
- [ ] **Fase 4:** Exportar los datos a formato CSV/Excel.
- [ ] **Fase 5:** (Futuro) Crear una interfaz gráfica o web sencilla.

## Estructura de datos
Por ahora, cada concepto almacenará la siguiente información:
- ID único
- Término
- Idioma (ES, EN, etc.)
- Definición

---
*Proyecto creado para aprender y practicar programación y gestión terminológica.*
