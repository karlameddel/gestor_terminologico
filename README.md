# 📚 Gestor Terminológico

¡Bienvenido/a a mi repositorio!

Esta herramienta nace gracias a la colaboración con una compañera estudiante de **Traducción e Interpretación**. Ella aporta la visión experta, identifica las necesidades reales del sector y define la lógica conceptual que requiere un traductor profesional. Mi labor consiste en tomar todas esas ideas, diseñar la arquitectura de la base de datos y escribir el código para convertirlas en una aplicación funcional. 

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

## Estructura de la Base de Datos
Para garantizar la integridad y la independencia de los términos, hemos diseñado un modelo de dos tablas vinculadas:

### 1. Tabla `Conceptos_ES` (Origen)
Es el núcleo del gestor. Cada entrada representa un concepto único definido en el idioma base.
- **ID único:** Identificador autoincremental para cada concepto.
- **Área:** Categoría temática (ej. Medicina, Informática, Legal).
- **Término ES:** El término en español que actúa como ancla.
- **Definición ES:** Definición detallada del concepto en español.

### 2. Tabla `Traducciones` (Destino)
Almacena las equivalencias en otros idiomas vinculadas al concepto original mediante el ID.
- **Idioma:** Código del idioma destino (ej. EN, FR, DE).
- **Término Traducido:** La palabra equivalente en el idioma destino.
- **Vínculo (FK):** Referencia directa al ID del concepto original en español.

---
*Proyecto simplificado creado para aprender y practicar programación y gestión terminológica.*
