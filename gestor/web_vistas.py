"""Pantallas HTML de la interfaz web. Son funciones que reciben datos ya preparados
y devuelven texto: no tocan la base de datos ni el servidor.

Todo lo que viene de los datos del usuario pasa por esc(), que convierte
caracteres como < o & para que nunca se interpreten como HTML."""
import html

CSS = """
:root{--fondo:#f6f7f9;--tarjeta:#fff;--texto:#1d2330;--suave:#5b6577;--borde:#d9dde5;
--acento:#2457c5;--sobre-acento:#fff;--ok-fondo:#e3f4e8;--ok:#14602b;--error-fondo:#fbe5e5;--error:#8c1d1d}
@media (prefers-color-scheme:dark){:root{--fondo:#14171d;--tarjeta:#1d222b;--texto:#e8eaee;--suave:#a0a8b8;
--borde:#323a48;--acento:#6b9cff;--sobre-acento:#0b1020;--ok-fondo:#17331f;--ok:#8fe0a6;--error-fondo:#3a1b1b;--error:#ffb4b4}}
*{box-sizing:border-box}
body{margin:0;font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--fondo);color:var(--texto)}
header{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:.6rem 1.5rem;
padding:.8rem 1.2rem;background:var(--tarjeta);border-bottom:1px solid var(--borde)}
.marca{font-weight:700;color:var(--texto);text-decoration:none}
nav{display:flex;flex-wrap:wrap;align-items:center;gap:.4rem 1.2rem}
nav form{margin:0}
a,.enlace{color:var(--acento);text-decoration:none;background:none;border:0;padding:0;font:inherit;cursor:pointer}
a:hover,.enlace:hover{text-decoration:underline}
main{max-width:1100px;margin:0 auto;padding:1.2rem}
h1{font-size:1.4rem;margin:.2rem 0 1rem}
h2{font-size:1.1rem;margin:1.6rem 0 .6rem}
.tarjeta{background:var(--tarjeta);border:1px solid var(--borde);border-radius:10px;padding:1rem 1.2rem;margin:1rem 0}
.aviso{padding:.7rem 1rem;border-radius:8px;margin:0 0 1rem}
.aviso.ok{background:var(--ok-fondo);color:var(--ok)}
.aviso.error{background:var(--error-fondo);color:var(--error)}
.suave{color:var(--suave)}
input,button,select{font:inherit}
input[type=text],input:not([type]),input[type=file]{width:100%;padding:.45rem .6rem;border:1px solid var(--borde);
border-radius:6px;background:var(--fondo);color:var(--texto)}
button{padding:.45rem .9rem;border-radius:6px;border:1px solid var(--borde);background:var(--tarjeta);
color:var(--texto);cursor:pointer}
button.principal{background:var(--acento);border-color:var(--acento);color:var(--sobre-acento);font-weight:600}
button.peligro{color:var(--error)}
button:hover{filter:brightness(.96)}
.rejilla{display:grid;grid-template-columns:1fr 1fr;gap:.8rem 1rem;align-items:end}
.rejilla label{display:flex;flex-direction:column;gap:.2rem;font-size:.9rem;color:var(--suave)}
.rejilla .ancha{grid-column:1/-1}
.casilla{flex-direction:row!important;align-items:center;gap:.5rem!important}
.casilla input{width:auto}
.buscador{display:flex;gap:.5rem;margin:0 0 1rem}
.tabla{overflow-x:auto}
table{width:100%;border-collapse:collapse;background:var(--tarjeta);border:1px solid var(--borde)}
th,td{text-align:left;padding:.55rem .7rem;border-bottom:1px solid var(--borde);vertical-align:top}
th{font-size:.85rem;color:var(--suave);font-weight:600}
td.acciones{white-space:nowrap}
.fila-trad{display:grid;grid-template-columns:5rem 1fr auto auto;gap:.5rem;margin:.4rem 0;align-items:center}
summary{cursor:pointer;font-weight:600}
@media (max-width:640px){.rejilla{grid-template-columns:1fr}.fila-trad{grid-template-columns:4rem 1fr}}
"""


def esc(valor):
    return html.escape("" if valor is None else str(valor), quote=True)


def pagina(titulo, cuerpo, mensaje="", tipo="ok"):
    tipo = "error" if tipo == "error" else "ok"
    aviso = f'<div class="aviso {tipo}" role="status">{esc(mensaje)}</div>' if mensaje else ""
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titulo)} · Gestor terminológico</title><style>{CSS}</style></head>
<body>
<header>
  <a class="marca" href="/">📚 Gestor terminológico</a>
  <nav>
    <a href="/">Diccionario</a>
    <a href="/importar">Importar CSV</a>
    <a href="/exportar">Exportar CSV</a>
    <form method="post" action="/apagar" onsubmit="return confirm('¿Cerrar el programa?')">
      <button class="enlace" type="submit">Cerrar programa</button></form>
  </nav>
</header>
<main>{aviso}{cuerpo}</main>
</body></html>"""


# ---------- Diccionario ----------

def _traducciones_en_linea(traducciones):
    if not traducciones:
        return '<span class="suave">—</span>'
    return "<br>".join(f"<b>{esc(idioma)}</b> {esc(', '.join(terminos))}"
                       for idioma, terminos in traducciones)


def formulario_nuevo(valores=None, abierto=False):
    v = valores or {}
    marcada = " checked" if "otro_significado" in v else ""
    return f"""<details class="tarjeta"{' open' if abierto else ''}>
<summary>➕ Añadir un término</summary>
<form method="post" action="/concepto/nuevo" class="rejilla" style="margin-top:.8rem">
  <label>Término en español <input name="termino" required value="{esc(v.get('termino'))}"></label>
  <label>Área <input name="area" required value="{esc(v.get('area'))}" placeholder="Informática, Medicina..."></label>
  <label class="ancha">Definición <input name="definicion" value="{esc(v.get('definicion'))}"></label>
  <label class="ancha casilla"><input type="checkbox" name="otro_significado"{marcada}>
    Este término ya existe y es <b>otro significado</b> (entonces la definición es obligatoria)</label>
  <div class="ancha"><button class="principal" type="submit">Guardar término</button></div>
</form></details>"""


def vista_indice(conceptos, consulta="", valores=None, abrir_formulario=False,
                 mensaje="", tipo="ok"):
    """`conceptos`: lista de dicts con id, termino, area, definicion y
    traducciones (lista de (idioma, [términos]))."""
    filas = "".join(
        f"""<tr><td><a href="/concepto/{c['id']}"><b>{esc(c['termino'])}</b></a></td>
<td>{esc(c['area'])}</td><td>{esc(c['definicion']) or '<span class="suave">—</span>'}</td>
<td>{_traducciones_en_linea(c['traducciones'])}</td>
<td class="acciones"><a href="/concepto/{c['id']}">Editar</a></td></tr>"""
        for c in conceptos)

    if conceptos:
        tabla = f"""<div class="tabla"><table>
<thead><tr><th>Término (ES)</th><th>Área</th><th>Definición</th><th>Traducciones</th><th></th></tr></thead>
<tbody>{filas}</tbody></table></div>"""
    elif consulta:
        tabla = f'<p class="suave">No hay resultados para «{esc(consulta)}».</p>'
    else:
        tabla = '<p class="suave">Todavía no hay ningún término. Añade el primero arriba o importa un CSV.</p>'

    quitar = ' <a href="/">Quitar filtro</a>' if consulta else ""
    cuerpo = f"""<h1>Diccionario</h1>
{formulario_nuevo(valores, abrir_formulario)}
<form method="get" action="/" class="buscador">
  <input name="q" value="{esc(consulta)}" placeholder="Buscar en términos, definiciones, áreas y traducciones (sin tildes ni mayúsculas)" autofocus>
  <button type="submit">Buscar</button></form>
<p class="suave">{len(conceptos)} resultado(s){quitar}</p>
{tabla}"""
    return pagina("Diccionario", cuerpo, mensaje, tipo)


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

    cuerpo = f"""<p><a href="/">← Volver al diccionario</a></p>
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
  <div class="ancha"><button type="submit">➕ Añadir traducción</button></div>
</form>

<h2>Zona delicada</h2>
<form method="post" action="/concepto/{c['id_concepto']}/borrar"
  onsubmit="return confirm('¿Borrar este término y todas sus traducciones? No se puede deshacer.')">
  <button class="peligro" type="submit">🗑️ Borrar este término y sus traducciones</button>
</form>"""
    return pagina(c["termino_es"], cuerpo, mensaje, tipo)


# ---------- Importar ----------

# Texto fijo (sin datos del usuario). El navegador envía el archivo tal cual al
# programa; todo lo que se pinta en pantalla se hace con textContent, nunca con HTML.
CUERPO_IMPORTAR = """<h1>Importar desde CSV</h1>
<div class="tarjeta">
<p>Sube un CSV de Excel o de Google Sheets con las columnas <b>Área</b>, <b>Definición</b>,
<b>ES</b> y una columna por idioma (EN, FR...). Varias traducciones en una celda se separan con <b>|</b>.</p>
<p class="suave">Primero se revisa el archivo y se te muestra un resumen. No se guarda nada hasta que lo confirmes.</p>
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
    return pagina("Importar", CUERPO_IMPORTAR)


# ---------- Otras ----------

def vista_apagado():
    return pagina("Cerrado", """<h1>Programa cerrado</h1>
<p>Ya puedes cerrar esta pestaña. Para volver a usar el gestor, ábrelo de nuevo.</p>""")


def vista_error(estado, texto):
    return pagina(f"Error {estado}", f"""<h1>{esc(texto)}</h1>
<p><a href="/">← Volver al diccionario</a></p>""", tipo="error")