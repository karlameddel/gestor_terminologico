"""Pantallas HTML de la interfaz web. Son funciones que reciben datos ya preparados
y devuelven texto: no tocan la base de datos ni el servidor.

Todo lo que viene de los datos del usuario pasa por esc(), que convierte
caracteres como < o & para que nunca se interpreten como HTML."""
import html

CSS = """
:root{
  --papel:#f6f0e4;--hoja:#fbf7ee;--tinta:#2b2620;--suave:#6b6254;--linea:#ddd2bd;--linea-fuerte:#b9ab8f;
  --acento:#2f5d50;--sobre-acento:#fbf7ee;--rojo:#8a3b2e;
  --ok-fondo:#e3ead9;--ok:#2f5d50;--error-fondo:#f1dad2;--error:#8a3b2e;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
@media (prefers-color-scheme:dark){:root{
  --papel:#1d1a16;--hoja:#26221c;--tinta:#ece4d4;--suave:#a99f8c;--linea:#3a342b;--linea-fuerte:#575043;
  --acento:#8fc1ae;--sobre-acento:#17211d;--rojo:#e0897a;
  --ok-fondo:#223228;--ok:#a9d6c3;--error-fondo:#3b2420;--error:#f0a698}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--papel);color:var(--tinta);font:17px/1.65 var(--serif)}
a{color:var(--acento);text-decoration-thickness:1px;text-underline-offset:.2em}
a:hover{text-decoration-thickness:2px}
:focus-visible{outline:2px solid var(--acento);outline-offset:2px;border-radius:2px}

header{max-width:820px;margin:0 auto;padding:1.6rem 1.2rem 0}
.cabecera{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:.4rem 2rem;
  padding-bottom:.9rem;border-bottom:3px double var(--linea-fuerte)}
.marca{font-size:1.55rem;font-weight:700;letter-spacing:.01em;color:var(--tinta);text-decoration:none}
nav{display:flex;flex-wrap:wrap;align-items:baseline;gap:.2rem 1.4rem;font:.95rem var(--sans)}
nav a{color:var(--suave);text-decoration:none;padding:.15rem 0;border-bottom:2px solid transparent}
nav a:hover{color:var(--tinta)}
nav a[aria-current=page]{color:var(--tinta);border-bottom-color:var(--acento)}
nav form{margin:0}
.enlace{font:inherit;color:var(--suave);background:none;border:0;padding:.15rem 0;cursor:pointer}
.enlace:hover{color:var(--rojo)}

main{max-width:820px;margin:0 auto;padding:1.6rem 1.2rem 4rem}
h1{font-size:2rem;line-height:1.2;margin:.2rem 0 1.1rem;font-weight:700}
h2{font-size:1.25rem;margin:2.2rem 0 .7rem;font-weight:700}
p{margin:.5rem 0 1rem;max-width:68ch}
.suave{color:var(--suave)}
.pequeno{font:.9rem var(--sans);color:var(--suave)}

.aviso{padding:.7rem 1rem;margin:0 0 1.4rem;border-left:4px solid;font:.95rem/1.5 var(--sans)}
.aviso.ok{background:var(--ok-fondo);color:var(--ok);border-color:var(--ok)}
.aviso.error{background:var(--error-fondo);color:var(--error);border-color:var(--error)}

input,button,select{font:1rem var(--sans)}
input[type=text],input:not([type]),input[type=file]{width:100%;padding:.55rem .7rem;border:1px solid var(--linea-fuerte);
  border-radius:3px;background:var(--hoja);color:var(--tinta)}
input::placeholder{color:var(--suave);opacity:.8}
input[type=checkbox]{accent-color:var(--acento);width:1.1rem;height:1.1rem}
button{padding:.5rem 1rem;border-radius:3px;border:1px solid var(--linea-fuerte);background:var(--hoja);
  color:var(--tinta);cursor:pointer}
button:hover{border-color:var(--tinta)}
button.principal{background:var(--acento);border-color:var(--acento);color:var(--sobre-acento);font-weight:600}
button.principal:hover{filter:brightness(1.1)}
button.peligro{color:var(--rojo);border-color:var(--rojo);background:transparent}
button:disabled{opacity:.55;cursor:default}

.tarjeta{background:var(--hoja);border:1px solid var(--linea);border-radius:3px;padding:1.1rem 1.3rem;margin:1.1rem 0}
.rejilla{display:grid;grid-template-columns:1fr 1fr;gap:.9rem 1.1rem;align-items:end}
.rejilla label{display:flex;flex-direction:column;gap:.3rem;font:.9rem var(--sans);color:var(--suave)}
.rejilla .ancha{grid-column:1/-1}
.casilla{flex-direction:row!important;align-items:center;gap:.6rem!important}
.casilla input{width:1.1rem;flex:none}
details.tarjeta>summary{cursor:pointer;font:600 1rem var(--sans);color:var(--acento)}

.buscador{display:flex;gap:.6rem;margin:0 0 .6rem}
.buscador input{font-size:1.1rem;padding:.7rem .9rem}
.recuento{font:.9rem var(--sans);color:var(--suave);margin:.4rem 0 1.4rem}

.entrada{padding:1.15rem 0 1.2rem;border-top:1px solid var(--linea)}
.entrada:last-of-type{border-bottom:1px solid var(--linea)}
.entrada .cabeza{display:flex;flex-wrap:wrap;align-items:baseline;gap:.2rem .8rem}
.entrada h2{font-size:1.45rem;margin:0;line-height:1.25}
.entrada h2 a{color:var(--tinta);text-decoration:none}
.entrada h2 a:hover{color:var(--acento);text-decoration:underline}
.area{font-style:italic;color:var(--suave)}
.entrada .editar{margin-left:auto;font:.9rem var(--sans)}
.def{margin:.35rem 0 .5rem}
.trads{margin:.25rem 0 0;display:grid;grid-template-columns:2.6rem 1fr;gap:.1rem .4rem;max-width:none}
.idioma{font:700 .85rem var(--sans);color:var(--acento);padding-top:.2rem}

.fila-trad{display:grid;grid-template-columns:5rem 1fr auto auto;gap:.5rem;margin:.5rem 0;align-items:center}
summary{cursor:pointer}
.vacio{padding:1.6rem 0;color:var(--suave)}
.migas{font:.95rem var(--sans);margin:0 0 .6rem}

@media (max-width:640px){
  body{font-size:16px}
  h1{font-size:1.6rem}
  .rejilla{grid-template-columns:1fr}
  .fila-trad{grid-template-columns:4rem 1fr}
  .buscador{flex-direction:column}
  .entrada .editar{margin-left:0}}
@media (prefers-reduced-motion:no-preference){
  button,a,input{transition:border-color .15s,color .15s,filter .15s}}
"""


def esc(valor):
    return html.escape("" if valor is None else str(valor), quote=True)


def pagina(titulo, cuerpo, mensaje="", tipo="ok", activa=""):
    tipo = "error" if tipo == "error" else "ok"
    aviso = f'<div class="aviso {tipo}" role="status">{esc(mensaje)}</div>' if mensaje else ""

    def enlace(ruta, texto, clave):
        actual = ' aria-current="page"' if clave == activa else ""
        return f'<a href="{ruta}"{actual}>{texto}</a>'

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titulo)} · Gestor terminológico</title><style>{CSS}</style></head>
<body>
<header>
  <div class="cabecera">
    <a class="marca" href="/">Gestor terminológico</a>
    <nav>
      {enlace("/", "Diccionario", "diccionario")}
      {enlace("/importar", "Importar", "importar")}
      {enlace("/exportar", "Exportar", "exportar")}
      <form method="post" action="/apagar" onsubmit="return confirm('¿Cerrar el programa?')">
        <button class="enlace" type="submit">Cerrar programa</button></form>
    </nav>
  </div>
</header>
<main>{aviso}{cuerpo}</main>
</body></html>"""


# ---------- Diccionario ----------

def _traducciones_en_linea(traducciones):
    if not traducciones:
        return ""
    filas = "".join(f'<span class="idioma">{esc(idioma)}</span><span>{esc(", ".join(terminos))}</span>'
                    for idioma, terminos in traducciones)
    return f'<p class="trads">{filas}</p>'


def formulario_nuevo(valores=None, abierto=False):
    v = valores or {}
    marcada = " checked" if "otro_significado" in v else ""
    return f"""<details class="tarjeta"{' open' if abierto else ''}>
<summary>Añadir un término</summary>
<form method="post" action="/concepto/nuevo" class="rejilla" style="margin-top:1rem">
  <label>Término en español <input name="termino" required value="{esc(v.get('termino'))}"></label>
  <label>Área <input name="area" required value="{esc(v.get('area'))}" placeholder="Informática, Medicina..."></label>
  <label class="ancha">Definición <input name="definicion" value="{esc(v.get('definicion'))}"></label>
  <label class="ancha casilla"><input type="checkbox" name="otro_significado"{marcada}>
    Este término ya existe y es otro significado (entonces la definición es obligatoria)</label>
  <div class="ancha"><button class="principal" type="submit">Guardar término</button></div>
</form></details>"""


def vista_indice(conceptos, consulta="", valores=None, abrir_formulario=False,
                 mensaje="", tipo="ok"):
    """`conceptos`: lista de dicts con id, termino, area, definicion y
    traducciones (lista de (idioma, [términos]))."""
    entradas = "".join(
        f"""<article class="entrada">
<div class="cabeza"><h2><a href="/concepto/{c['id']}">{esc(c['termino'])}</a></h2>
<span class="area">{esc(c['area'])}</span>
<a class="editar" href="/concepto/{c['id']}">Editar</a></div>
{f'<p class="def">{esc(c["definicion"])}</p>' if c['definicion'] else ''}
{_traducciones_en_linea(c['traducciones'])}
</article>"""
        for c in conceptos)

    if conceptos:
        lista = entradas
    elif consulta:
        lista = f'<p class="vacio">No hay resultados para «{esc(consulta)}». Prueba con otra palabra o una parte de ella.</p>'
    else:
        lista = ('<p class="vacio">Todavía no hay ningún término. Añade el primero con el formulario '
                 'de arriba o importa un glosario en CSV.</p>')

    quitar = ' <a href="/">Quitar filtro</a>' if consulta else ""
    cuerpo = f"""<h1>Diccionario</h1>
<form method="get" action="/" class="buscador" role="search">
  <input name="q" value="{esc(consulta)}" aria-label="Buscar"
    placeholder="Busca un término o una traducción" autofocus>
  <button class="principal" type="submit">Buscar</button></form>
<p class="recuento">{len(conceptos)} resultado(s). La búsqueda ignora tildes y mayúsculas.{quitar}</p>
{formulario_nuevo(valores, abrir_formulario)}
{lista}"""
    return pagina("Diccionario", cuerpo, mensaje, tipo, activa="diccionario")


# ---------- Un concepto ----------

def vista_concepto(c, traducciones, mensaje="", tipo="ok"):
    """`c`: fila del concepto. `traducciones`: filas con id_termino, idioma y termino."""
    filas = "".join(
        f"""<form method="post" action="/traduccion/{t['id_termino']}/editar" class="fila-trad">
  <input name="idioma" value="{esc(t['idioma'])}" maxlength="3" required aria-label="Idioma">
  <input name="termino" value="{esc(t['termino'])}" required aria-label="Traducción">
  <button type="submit">Guardar</button>
  <button class="peligro" type="submit" formaction="/traduccion/{t['id_termino']}/borrar"
    onclick="return confirm('¿Borrar esta traducción?')">Borrar</button>
</form>"""
        for t in traducciones) or '<p class="suave">Todavía no tiene traducciones.</p>'

    cuerpo = f"""<p class="migas"><a href="/">Volver al diccionario</a></p>
<h1>{esc(c['termino_es'])}</h1>

<form method="post" action="/concepto/{c['id_concepto']}/editar" class="tarjeta rejilla">
  <label>Término en español <input name="termino" required value="{esc(c['termino_es'])}"></label>
  <label>Área <input name="area" required value="{esc(c['area'])}"></label>
  <label class="ancha">Definición <input name="definicion" value="{esc(c['definicion'])}"></label>
  <div class="ancha"><button class="principal" type="submit">Guardar cambios</button></div>
</form>

<h2>Traducciones</h2>
<div class="tarjeta">{filas}</div>

<form method="post" action="/concepto/{c['id_concepto']}/traduccion" class="tarjeta rejilla">
  <label>Idioma (2-3 letras: EN, FR, DE...) <input name="idioma" maxlength="3" required></label>
  <label>Traducción <input name="termino" required></label>
  <div class="ancha"><button type="submit">Añadir traducción</button></div>
</form>

<h2>Borrar</h2>
<form method="post" action="/concepto/{c['id_concepto']}/borrar"
  onsubmit="return confirm('¿Borrar este término y todas sus traducciones? No se puede deshacer.')">
  <button class="peligro" type="submit">Borrar este término y sus traducciones</button>
</form>"""
    return pagina(c["termino_es"], cuerpo, mensaje, tipo, activa="diccionario")


# ---------- Importar ----------

# Texto fijo (sin datos del usuario). El navegador envía el archivo tal cual al
# programa; todo lo que se pinta en pantalla se hace con textContent, nunca con HTML.
CUERPO_IMPORTAR = """<h1>Importar desde CSV</h1>
<div class="tarjeta">
<p>Sube un CSV de Excel o de Google Sheets con las columnas <b>Área</b>, <b>Definición</b>,
<b>ES</b> y una columna por idioma (EN, FR...). Varias traducciones en una celda se separan con <b>|</b>.</p>
<p class="pequeno">Primero se revisa el archivo y se te muestra un resumen. No se guarda nada hasta que lo confirmes.</p>
<div class="rejilla">
  <label class="ancha">Archivo CSV <input type="file" id="archivo" accept=".csv,.txt,text/csv"></label>
  <label class="ancha">Área para las filas que no la tengan (opcional) <input type="text" id="area"></label>
  <div class="ancha"><button class="principal" id="revisar" type="button">Revisar archivo</button></div>
</div></div>
<div id="resultado"></div>
<script>
const $ = (id) => document.getElementById(id);
function nodo(etiqueta, texto, clase) {
  const n = document.createElement(etiqueta);
  if (texto !== undefined) n.textContent = texto;
  if (clase) n.className = clase;
  return n;
}
function lista(titulo, lineas) {
  const caja = nodo('div', undefined, 'tarjeta');
  caja.append(nodo('b', titulo));
  const ul = document.createElement('ul');
  lineas.forEach((l) => ul.append(nodo('li', l)));
  caja.append(ul);
  return caja;
}
function mostrar(r) {
  const salida = $('resultado');
  salida.replaceChildren();
  if (!r.ok) { salida.append(nodo('div', r.error, 'aviso error')); return; }
  salida.append(lista('Resumen de la revisión', r.lineas));
  if (r.avisos.length) salida.append(lista('Conviene revisar', r.avisos));
  if (r.errores.length) salida.append(lista('Filas con problemas (no se importarán)', r.errores));
  if (!r.hay_cambios) { salida.append(nodo('p', 'No hay nada nuevo que guardar.', 'suave')); return; }
  const boton = nodo('button', 'Guardar estos cambios', 'principal');
  boton.onclick = async () => {
    boton.disabled = true;
    const rr = await (await fetch('/api/importar/confirmar', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({token: r.token})})).json();
    salida.replaceChildren();
    salida.append(nodo('div', rr.ok ? rr.mensaje : rr.error, 'aviso ' + (rr.ok ? 'ok' : 'error')));
    const volver = nodo('a', 'Ver el diccionario'); volver.href = '/'; salida.append(volver);
  };
  salida.append(boton);
}
$('revisar').onclick = async () => {
  const archivo = $('archivo').files[0];
  if (!archivo) { mostrar({ok: false, error: 'Elige primero un archivo CSV.'}); return; }
  try {
    const respuesta = await fetch('/api/importar/previsualizar', {
      method: 'POST',
      headers: {'X-Area': encodeURIComponent($('area').value), 'Content-Type': 'application/octet-stream'},
      body: await archivo.arrayBuffer()});
    mostrar(await respuesta.json());
  } catch (e) {
    mostrar({ok: false, error: 'No se pudo comunicar con el programa. ¿Sigue abierto?'});
  }
};
</script>"""


def vista_importar():
    return pagina("Importar", CUERPO_IMPORTAR, activa="importar")


# ---------- Otras ----------

def vista_apagado():
    return pagina("Cerrado", """<h1>Programa cerrado</h1>
<p>Ya puedes cerrar esta pestaña. Para volver a usar el gestor, ábrelo de nuevo.</p>""")


def vista_error(estado, texto):
    return pagina(f"Error {estado}", f"""<h1>{esc(texto)}</h1>
<p><a href="/">Volver al diccionario</a></p>""", tipo="error")