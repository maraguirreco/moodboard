import os
# --- INSTALACIÓN DE NAVEGADOR PARA LA NUBE ---
os.system("playwright install chromium")
# ---------------------------------------------

import streamlit as st
import json
import re
import ast
import base64
import time
import requests
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from PIL import Image
from openai import OpenAI
from duckduckgo_search import DDGS

# === 🎨 CONFIGURACIÓN DE IDENTIDAD VELOVE ===
LOGO_URL = "https://www.dropbox.com/scl/fi/gftit3er4w0ty3y31r0oy/logo-velove-2026.svg?rlkey=lmmcyddkzhv1qxegy6bgnjvj9&st=2n701c15&raw=1"
COLOR_FONDO = "#e4d2c2"
COLOR_TEXTO = "#001c19"
COLOR_BOTON = "#ff1d4e"
COLOR_BOTON_HOVER = "#e01742"
# ============================================

st.set_page_config(page_title="Velove | Benchmarking AI", page_icon="🎨", layout="wide")

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Work+Sans:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap');
    html, body, [class*="css"], .stApp {{ font-family: 'Work Sans', sans-serif !important; background-color: {COLOR_FONDO} !important; color: {COLOR_TEXTO} !important; }}
    .stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div {{ background-color: #ffffff !important; color: {COLOR_TEXTO} !important; border-radius: 8px !important; border: 1px solid {COLOR_TEXTO} !important; font-family: 'Work Sans', sans-serif !important; }}
    div.stButton > button:first-child {{ background-color: {COLOR_BOTON} !important; color: #ffffff !important; border-radius: 8px !important; border: none !important; font-weight: 600 !important; font-family: 'Work Sans', sans-serif !important; padding: 12px 24px !important; transition: all 0.3s ease !important; }}
    div.stButton > button:first-child:hover {{ background-color: {COLOR_BOTON_HOVER} !important; color: #ffffff !important; }}
    h1, h2, h3, h4, h5, h6, p, span, label {{ color: {COLOR_TEXTO} !important; font-family: 'Work Sans', sans-serif !important; }}
    .stProgress > div > div > div > div {{ background-color: {COLOR_BOTON} !important; }}
    </style>
""", unsafe_allow_html=True)

OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

def parsear_json_llm(texto):
    """ Repara cualquier error de formato o sintaxis devuelto por la IA """
    match = re.search(r'\[.*\]', texto, re.DOTALL)
    if not match: return []
    raw_json = match.group(0)
    raw_json_clean = re.sub(r',\s*([\]}])', r'\1', raw_json)
    try: return json.loads(raw_json_clean)
    except Exception: pass
    try: return ast.literal_eval(raw_json_clean)
    except Exception: pass
    try:
        raw_json_fix = raw_json_clean.replace("'", '"')
        raw_json_fix = re.sub(r',\s*([\]}])', r'\1', raw_json_fix)
        return json.loads(raw_json_fix)
    except Exception:
        return []

# === 🕸️ BÚSQUEDA WEB BLINDADA CON FILTROS DE CALIDAD ===
def buscar_urls_reales(query, max_results=12):
    urls_validas = []
    bad_domains = [
        "facebook", "instagram", "linkedin", "youtube", "tiktok", "twitter", "pinterest", 
        "google.com", "wikipedia", "yelp", "tripadvisor", "computrabajo", "paginasamarillas",
        "linguee", "collinsdictionary", "wordreference", "cambridge", "merriam-webster", 
        "rae.es", "reverso", "dictionary", "thesaurus", "traductor", "translate"
    ]
    bad_keywords = ["diccionario", "dictionary", "traducción", "translation", "significado", "herramientas lingüísticas", "definición", "lingüística"]
    
    for intento in range(2):
        try:
            time.sleep(1)
            results = list(DDGS().text(query, max_results=25))
            if results:
                for r in results:
                    url = r.get("href", "").lower()
                    title = r.get("title", "").split("-")[0].split("|")[0].strip()
                    title_lower = title.lower()
                    
                    if not url or any(bad in url for bad in bad_domains):
                        continue
                    if any(key in title_lower for key in bad_keywords):
                        continue
                        
                    urls_validas.append({"nombre": title, "url": r.get("href", "")})
                    if len(urls_validas) >= max_results: break
                if urls_validas: break
        except Exception:
            time.sleep(1)
    return urls_validas

def buscar_pauta_o_grafico(nombre_brand, sector):
    try:
        time.sleep(0.5)
        query = f"{nombre_brand} {sector} publicidad pauta redes sociales"
        results = list(DDGS().images(query, max_results=2))
        for r in results:
            img_url = r.get("image", "")
            if img_url:
                resp = requests.get(img_url, timeout=4)
                if resp.status_code == 200:
                    encoded = base64.b64encode(resp.content).decode('utf-8')
                    return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        pass
    return ""

def comprimir_y_convertir_base64(img_path):
    try:
        if not os.path.exists(img_path): return ""
        with Image.open(img_path) as img:
            img = img.convert('RGB')
            img.thumbnail((400, 400))
            from io import BytesIO
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=65)
            encoded = base64.b64encode(buffered.getvalue()).decode('utf-8')
            return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        return ""

def extraer_colores_css(page):
    try:
        js_script = """
        () => {
            const colors = new Set();
            const theme = document.querySelector('meta[name="theme-color"]');
            if (theme && theme.content) colors.add(theme.content);
            const elementos = document.querySelectorAll('header, nav, button, a.btn, .button, h1, .primary, .bg-primary');
            elementos.forEach(el => {
                const style = window.getComputedStyle(el);
                if (style.backgroundColor && style.backgroundColor !== 'rgba(0, 0, 0, 0)') colors.add(style.backgroundColor);
                if (style.color && style.color !== 'rgba(0, 0, 0, 0)') colors.add(style.color);
            });
            return Array.from(colors);
        }
        """
        raw_colors = page.evaluate(js_script)
        hex_colors = []
        for c in raw_colors:
            if 'rgb' in c:
                nums = [int(n) for n in re.findall(r'\d+', c)[:3]]
                if len(nums) == 3:
                    r, g, b = nums
                    if sum(nums) > 700 or sum(nums) < 50: continue
                    if abs(r - g) < 10 and abs(g - b) < 10: continue
                    hex_code = '#{:02x}{:02x}{:02x}'.format(r, g, b)
                    if hex_code not in hex_colors: hex_colors.append(hex_code)
            elif c.startswith('#') and len(c) in [4, 7]:
                if c not in hex_colors: hex_colors.append(c)
            if len(hex_colors) >= 5: break
        return hex_colors
    except Exception:
        return []

def extraer_colores_de_imagen(img_path, num_colores=4):
    try:
        if not os.path.exists(img_path): return []
        with Image.open(img_path) as img:
            img = img.convert('RGB')
            img = img.resize((150, 150))
            result = img.quantize(colors=15)
            palette = result.getpalette()
            color_counts = sorted(result.getcolors(), reverse=True, key=lambda x: x[0])
            
            hex_colors = []
            for count, index in color_counts:
                r = palette[index*3]
                g = palette[index*3+1]
                b = palette[index*3+2]
                
                if (r > 235 and g > 235 and b > 235) or (r < 25 and g < 25 and b < 25): continue
                if abs(r - g) < 15 and abs(g - b) < 15 and abs(r - b) < 15: continue
                    
                hex_code = f"#{r:02x}{g:02x}{b:02x}"
                if hex_code not in hex_colors: hex_colors.append(hex_code)
                if len(hex_colors) >= num_colores: break
            return hex_colors
    except Exception:
        return []

col_logo, col_title = st.columns([1, 4])
with col_logo:
    st.image(LOGO_URL, width=150)
with col_title:
    st.title("Agente Estratega de Marca & Benchmarking")
    st.markdown("Genera matrices de benchmarking con inteligencia de mercado y análisis de marcas de alto nivel.")

st.markdown("---")

with st.container():
    st.subheader("📋 Brief del Cliente e Inteligencia de Mercado")
    col1, col2 = st.columns(2)
    with col1:
        marca = st.text_input("Nombre de la marca:", placeholder="Ej. Aurora Travel")
        sector = st.text_input("Sector / Industria:", placeholder="Ej. Agencia de Marketing Digital B2B")
        pais = st.text_input("🌍 País de Operación:", placeholder="Ej. Colombia, México, España")
    with col2:
        ciudad = st.text_input("🏙️ Ciudad / Región (Local):", placeholder="Ej. Cali, CDMX, Madrid")
        producto = st.text_area("Producto / Core:", placeholder="Ej. Generación de leads B2B, SEO técnico y pauta en LinkedIn...", height=68)
    
    st.markdown("---")
    
    col3, col4 = st.columns(2)
    with col3:
        modelo_negocio_opt = st.selectbox(
            "💼 Modelo de Negocio (Opcional):",
            ["General / No especificar (Búsqueda amplia)", "B2B (Empresa a Empresa)", "B2C (Empresa a Consumidor)", "B2B2C", "D2C (Directo al Consumidor)", "Marketplace", "SaaS (Software como Servicio)", "ONG / Sin Ánimo de Lucro", "Gobierno / Sector Público", "Otro (Escribir personalizado)"]
        )
        if modelo_negocio_opt == "Otro (Escribir personalizado)":
            modelo_negocio_final = st.text_input("Especifica el modelo de negocio:", placeholder="Ej. Franquicias").strip() or "General"
        elif "General" in modelo_negocio_opt:
            modelo_negocio_final = "General / No especificado"
        else:
            modelo_negocio_final = modelo_negocio_opt

    with col4:
        competidores_fijos = st.text_input("🎯 Competidores locales conocidos (Opcional - separados por coma):", placeholder="Ej. Obility, Demandbase")

if st.button("🔥 Ejecutar Benchmark Estratégico", type="primary"):
    if not marca or not sector or not pais or not ciudad or not producto:
        st.error("Por favor completa los campos: Marca, Sector, País, Ciudad y Producto.")
    else:
        status_box = st.empty()
        progress_bar = st.progress(0)
        
        status_box.info(f"🔍 Fase 1/3: Rastreando líderes de mercado en {ciudad}, nacional en {pais} e inspiración especializada...")
        
        sector_corto = sector.split(",")[0].split("/")[0].strip()
        producto_corto = producto.split(",")[0].split(".")[0].strip()[:30]
        
        # Búsquedas Web Optimizadas para encontrar "Autoridad" y "Prestigio"
        locales_web = buscar_urls_reales(f"mejores agencias empresas {sector_corto} {ciudad} {pais}", max_results=10)
        nacionales_web = buscar_urls_reales(f"top empresas líderes {sector_corto} {pais}", max_results=10)
        inter_web = buscar_urls_reales(f"top rated global companies agencies {sector_corto} {producto_corto}", max_results=10)
        
        # 🎯 BÚSQUEDA DE INSPIRACIÓN HIPER-ESPECÍFICA (Cruzando Sector + Producto)
        insp_web = buscar_urls_reales(f"{sector_corto} {producto_corto} branding identity design (site:awwwards.com OR site:thedieline.com OR site:cosmos.so OR site:reallygoodemails.com OR site:brandarchive.xyz OR site:itsnicethat.com OR site:fastcompany.com)", max_results=8)
        
        fijos_lista = []
        if competidores_fijos.strip():
            for item in competidores_fijos.split(","):
                item_clean = item.strip()
                if item_clean:
                    found = buscar_urls_reales(f"{item_clean} sitio web oficial", max_results=1)
                    if found:
                        fijos_lista.append(found[0])
                    else:
                        fijos_lista.append({"nombre": item_clean, "url": f"https://www.google.com/search?q={item_clean}"})

        todos_los_hallazgos = fijos_lista + locales_web + nacionales_web + inter_web + insp_web
        
        hallazgos_unicos = []
        urls_vistas = set()
        for item in todos_los_hallazgos:
            domain = urlparse(item["url"]).netloc.replace("www.", "")
            if domain and domain not in urls_vistas:
                urls_vistas.add(domain)
                hallazgos_unicos.append(item)

        competidores = []

        if len(hallazgos_unicos) >= 3:
            status_box.info("🧠 Evaluando marcas con filtro de élite y relevancia del mercado...")
            prompt_descubrimiento = f"""
            Actúa como Senior Market Research Analyst.
            
            BRIEF DEL CLIENTE:
            - Marca: {marca}
            - Sector: {sector}
            - Producto / Core: {producto}
            - Ubicación: {ciudad}, {pais}
            - Modelo de Negocio: {modelo_negocio_final}
            
            AQUÍ ESTÁ LA BASE DE DATOS DE URLs REALES ENCONTRADAS EN WEB:
            {json.dumps(hallazgos_unicos)}
            
            ⛔ REGLAS Y CRITERIOS DE SELECCIÓN DE ÉLITE (APLICA LOS 4):
            1. FILTRO DE CORE REAL: Elige ÚNICAMENTE marcas o agencias comerciales reales que vendan {producto} dentro de {sector}.
            2. NO DICCIONARIOS: Elimina estrictamente sitios de definiciones, glosarios, diccionarios o agregadores.
            3. AUTORIDAD Y PRESTIGIO (NUEVO): Selecciona ESTRICTAMENTE a los líderes y referentes del mercado. Prioriza empresas que, según tu conocimiento, tengan alto tráfico web, premios, gran reconocimiento de marca o excelentes valoraciones (ej. en Clutch, Trustpilot, Google). IGNORA negocios pequeños, fantasmas o de dudosa reputación.
            4. INSPIRACIÓN: Selecciona referentes globales icónicos QUE PERTENEZCAN al mismo sector ({sector}) o resuelvan la misma necesidad.
            
            🎯 DESGLOSE REQUERIDO POR CATEGORÍAS:
            - 8 a 10 Locales (con presencia o base en {ciudad})
            - 8 a 10 Nacionales (con presencia en {pais})
            - 8 a 10 Internacionales (líderes globales del sector)
            - 4 a 6 Inspiración (referentes visuales y de branding afines al sector)
            
            Devuelve ÚNICAMENTE un arreglo JSON empezando por '[' y terminando por ']':
            [
                {{
                    "nombre": "Nombre Comercial Real",
                    "url": "URL Exacta Copiada del JSON",
                    "categoria": "Local / Nacional / Internacional / Inspiración",
                    "ubicacion": "Ciudad, País",
                    "colores_estimados": ["#HEX1", "#HEX2"],
                    "justificacion": "Por qué es un competidor relevante (Menciona su prestigio, autoridad en el mercado, reseñas o calidad comprobada)",
                    "servicios": "Servicios principales",
                    "propuesta_valor": "Propuesta de valor",
                    "diferencial": "Factor diferencial",
                    "comunicacion": "Estilo de comunicación"
                }}
            ]
            """
            
            try:
                res_descubrimiento = client.chat.completions.create(
                    model="openrouter/free",
                    messages=[{"role": "user", "content": prompt_descubrimiento}],
                    temperature=0.1
                )
                raw_content = res_descubrimiento.choices[0].message.content or ""
                competidores_ia = parsear_json_llm(raw_content)
                
                for comp in competidores_ia:
                    url_ia = comp.get("url", "")
                    domain_ia = urlparse(url_ia).netloc.replace("www.", "")
                    match_real = next((h for h in hallazgos_unicos if urlparse(h["url"]).netloc.replace("www.", "") == domain_ia), None)
                    if match_real:
                        comp["url"] = match_real["url"]
                        competidores.append(comp)
                    elif url_ia and "google.com" not in url_ia:
                        competidores.append(comp)
            except Exception:
                pass

        if len(competidores) < 5:
            status_box.warning("⚡ Generando Benchmark Estratégico mediante Memoria Neuronal Corporativa...")
            prompt_rescue = f"""
            Actúa como Senior Brand Strategist.
            Necesito un estudio de competencia de ÉLITE para la marca '{marca}' en el sector '{sector}' (Producto: {producto}) en {ciudad}, {pais}.
            
            🎯 DESGLOSE OBLIGATORIO DE MARCAS REALES DE ALTA AUTORIDAD:
            - 8 Locales / Nacionales ({ciudad}, {pais}) -> Selecciona a los LÍDERES del mercado con mejor reputación.
            - 8 Internacionales -> Solo los gigantes de la industria.
            - 5 Referentes globales de Branding / Inspiración alineados a {sector}
            
            Devuelve ÚNICAMENTE un arreglo JSON empezando por '[' y terminando por ']':
            [
                {{
                    "nombre": "Nombre Comercial Real",
                    "url": "https://www.sitioweboficialreal.com",
                    "categoria": "Local / Nacional / Internacional / Inspiración",
                    "ubicacion": "Ciudad, País",
                    "colores_estimados": ["#1e293b", "#0f172a"],
                    "justificacion": "Menciona su prestigio, autoridad de mercado o reconocimiento",
                    "servicios": "Servicios principales",
                    "propuesta_valor": "Propuesta de valor",
                    "diferencial": "Factor diferencial",
                    "comunicacion": "Tono de marca"
                }}
            ]
            """
            try:
                res_rescue = client.chat.completions.create(
                    model="openrouter/free",
                    messages=[{"role": "user", "content": prompt_rescue}],
                    temperature=0.2
                )
                competidores = parsear_json_llm(res_rescue.choices[0].message.content or "")
            except Exception:
                pass

        total_marcas = len(competidores)
        
        os.makedirs("assets", exist_ok=True)
        resultados_analisis = []
        
        status_box.info(f"📸 Fase 2/3: Capturando webs y analizando paletas de colores de {total_marcas} marcas reales...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_viewport_size({"width": 1280, "height": 800})
            
            for index, comp in enumerate(competidores, 1):
                progress_bar.progress(index / total_marcas * 0.7)
                
                nombre_comp = comp.get("nombre", f"Marca_{index}")
                url_comp = comp.get("url", "")
                colores_backup = comp.get("colores_estimados", ["#001c19", "#ff1d4e"])
                
                status_box.warning(f"({index}/{total_marcas}) Auditando visualmente: {nombre_comp}...")
                nombre_limpio = re.sub(r'\W+', '', nombre_comp).lower()
                screenshot_path = f"assets/{nombre_limpio}.jpg"
                
                colores_finales = []
                img_base64 = ""
                
                if url_comp and "google.com" not in url_comp and url_comp.startswith("http"):
                    try:
                        page.goto(url_comp, timeout=8000, wait_until="domcontentloaded")
                        time.sleep(1.5)
                        
                        colores_css = extraer_colores_css(page)
                        page.screenshot(path=screenshot_path, full_page=False, type="jpeg", quality=60)
                        colores_img = extraer_colores_de_imagen(screenshot_path)
                        
                        colores_finales = list(dict.fromkeys(colores_css + colores_img))
                        img_base64 = comprimir_y_convertir_base64(screenshot_path)
                    except Exception:
                        pass
                
                if len(colores_finales) < 2:
                    colores_finales = colores_backup
                
                pauta_base64 = buscar_pauta_o_grafico(nombre_comp, sector_corto)
                
                domain = urlparse(url_comp).netloc
                if "google.com" in domain or not domain:
                    logo_url = ""
                else:
                    logo_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
                
                resultados_analisis.append({
                    **comp, 
                    "colores": colores_finales[:4],
                    "img_b64": img_base64, 
                    "pauta_b64": pauta_base64,
                    "logo_url": logo_url
                })
            
            browser.close()
        
        status_box.info("🧠 Fase 3/3: Generando Dirección de Arte y Conclusiones Estratégicas...")
        progress_bar.progress(0.9)
        
        contexto_resumido = json.dumps([{
            "nombre": r.get("nombre", ""), "categoria": r.get("categoria", ""), 
            "diferencial": r.get("diferencial", "")
        } for r in resultados_analisis])
        
        prompt_insights = f"""
        Actúa como Senior Director de Arte y Estratega de Marca.
        Analiza las {total_marcas} empresas auditadas para la marca '{marca}' ({sector} - {producto}) en {ciudad}, {pais}.
        Matriz de competidores: {contexto_resumido}
        
        ⛔ INSTRUCCIÓN DE SALIDA ESTRICTA:
        Entrega ÚNICAMENTE código HTML directo usando exclusivamente las etiquetas <h3>, <ul>, <li>, <p> y <strong>.
        NO incluyas ninguna frase introductiva, markdown como ```html, meta-comentario ni texto fuera del HTML.
        
        <h3>📌 1. Patrones y Estándares del Sector</h3>
        <p>Análisis de tendencias de comunicación y códigos visuales comunes.</p>
        
        <h3>💡 2. Gaps y Oportunidades de Mercado</h3>
        <p>Espacios estratégicos desaprovechados por los competidores actuales.</p>
        
        <h3>🎨 3. Dirección de Arte Visual Recomendada</h3>
        <p>Pautas para estilo gráfico, colores, tipografía y tratamiento de imagen.</p>
        
        <h3>🚀 4. Posicionamiento Estratégico y Tono de Voz</h3>
        <p>Estrategia de diferenciación y estilo comunicativo recomendado.</p>
        """
        
        res_insights = client.chat.completions.create(
            model="openrouter/free",
            messages=[{"role": "user", "content": prompt_insights}],
            temperature=0.2
        )
        insights_raw = res_insights.choices[0].message.content or ""
        
        # Limpieza de markdown o texto innecesario para evitar el "We need to produce HTML"
        if "<h3>" in insights_raw:
            insights_html = insights_raw[insights_raw.find("<h3>"):]
            insights_html = insights_html.replace("```html", "").replace("```", "")
        else:
            insights_html = insights_raw
        
        progress_bar.progress(1.0)
        status_box.success(f"🎉 ¡Benchmark Completo de {total_marcas} Marcas verificado y generado!")
        
        tabla_html = ""
        for r in resultados_analisis:
            color_html = "".join([f'<div style="width:22px;height:22px;background:{c};border-radius:50%;display:inline-block;margin:2px;border:1px solid #ccc;" title="{c}"></div>' for c in r['colores']])
            
            logo_tag = f'<img src="{r["logo_url"]}" style="width:28px; height:28px; border-radius:4px; border:1px solid #ccc;" onerror="this.style.display=\'none\'">' if r.get("logo_url") else ''
            img_tag = f'<div style="margin-top:6px;"><span style="font-size:10px; font-weight:bold; color:#666;">🖥️ Captura Web:</span><br><img src="{r["img_b64"]}" style="width:100%; max-width:240px; border-radius:6px; border:1px solid #ddd;"></div>' if r.get("img_b64") else '<div style="background:#f0e2d5; padding:10px; border-radius:6px; color:#666; font-size:10px; margin-top:6px;">Web no disponible</div>'
            pauta_tag = f'<div style="margin-top:8px;"><span style="font-size:10px; font-weight:bold; color:{COLOR_BOTON};">📢 Pauta / Pieza Gráfica:</span><br><img src="{r["pauta_b64"]}" style="width:100%; max-width:240px; border-radius:6px; border:1px solid #ddd;"></div>' if r.get("pauta_b64") else ''
            
            tabla_html += f"""
            <tr>
                <td style="padding:14px; border-bottom:1px solid #d8c2b0; vertical-align:top;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
                        {logo_tag}
                        <div>
                            <strong style="font-size:14px; color:{COLOR_TEXTO};">{r.get("nombre", "Marca")}</strong><br>
                            <span style="font-size:10px; font-weight:700; color:{COLOR_BOTON}; text-transform:uppercase;">{r.get("categoria", "Competidor")}</span>
                        </div>
                    </div>
                    <p style="font-size:11px; margin:2px 0; color:#333;">📍 {r.get("ubicacion", "N/D")}</p>
                    <a href="{r.get("url", "#")}" target="_blank" style="font-size:11px; color:{COLOR_BOTON}; font-weight:600;">🌐 Sitio Web Oficial</a>
                    <p style="font-size:11px; color:#555; margin-top:6px; line-height:1.3;"><i>"{r.get("justificacion", "")}"</i></p>
                </td>
                <td style="padding:14px; border-bottom:1px solid #d8c2b0; font-size:12px; vertical-align:top; line-height:1.4;">
                    <p style="margin:0 0 6px 0;"><strong>Servicios:</strong> {r.get("servicios", "N/D")}</p>
                    <p style="margin:0 0 6px 0;"><strong>Propuesta:</strong> {r.get("propuesta_valor", "N/D")}</p>
                    <p style="margin:0;"><strong>Diferencial:</strong> {r.get("diferencial", "N/D")}</p>
                </td>
                <td style="padding:14px; border-bottom:1px solid #d8c2b0; vertical-align:top; text-align:center;">
                    <div style="margin-bottom:6px;">{color_html}</div>
                    {img_tag}
                    {pauta_tag}
                </td>
                <td style="padding:14px; border-bottom:1px solid #d8c2b0; font-size:12px; vertical-align:top; line-height:1.4;">
                    {r.get("comunicacion", "N/D")}
                </td>
            </tr>
            """
        
        html_final = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>Benchmark Velove: {marca}</title>
            <link rel="preconnect" href="[https://fonts.googleapis.com](https://fonts.googleapis.com)">
            <link rel="preconnect" href="[https://fonts.gstatic.com](https://fonts.gstatic.com)" crossorigin>
            <link href="[https://fonts.googleapis.com/css2?family=Work+Sans:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap](https://fonts.googleapis.com/css2?family=Work+Sans:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap)" rel="stylesheet">
            <style>
                body {{ font-family: 'Work Sans', sans-serif; padding: 40px; background-color: {COLOR_FONDO}; color: {COLOR_TEXTO}; line-height: 1.5; }}
                .container {{ max-width: 1400px; margin: 0 auto; }}
                .header {{ background-color: {COLOR_TEXTO}; color: {COLOR_FONDO}; padding: 30px; border-radius: 12px; margin-bottom: 30px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 8px 16px rgba(0,0,0,0.1); }}
                .header-info h1 {{ margin: 0 0 6px 0; font-size: 26px; font-weight: 700; color: {COLOR_FONDO}; }}
                .header-info p {{ margin: 0; opacity: 0.85; font-size: 13px; color: {COLOR_FONDO}; }}
                .logo-img {{ height: 50px; object-fit: contain; }}
                table {{ width: 100%; border-collapse: collapse; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 35px; }}
                th {{ background-color: {COLOR_TEXTO}; color: {COLOR_FONDO}; padding: 16px; text-align: left; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }}
                .insights-card {{ background: #ffffff; padding: 35px; border-radius: 12px; border-left: 6px solid {COLOR_BOTON}; box-shadow: 0 4px 10px rgba(0,0,0,0.05); line-height: 1.6; }}
                .insights-card h3 {{ color: {COLOR_TEXTO}; margin-top: 20px; font-size: 18px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="header-info">
                        <h1>📊 Matriz de Benchmarking Estratégico ({total_marcas} Marcas)</h1>
                        <p><strong>Cliente:</strong> {marca} &nbsp;|&nbsp; <strong>Sector:</strong> {sector} &nbsp;|&nbsp; <strong>Modelo:</strong> {modelo_negocio_final} &nbsp;|&nbsp; <strong>Ubicación:</strong> {ciudad}, {pais}</p>
                    </div>
                    <img src="{LOGO_URL}" class="logo-img" alt="Logo Velove">
                </div>
                
                <table>
                    <thead>
                        <tr>
                            <th width="25%">Marca & Ubicación</th>
                            <th width="30%">Análisis Estratégico</th>
                            <th width="25%">Identidad Visual (Web & Pauta)</th>
                            <th width="20%">Tono & Comunicación</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tabla_html}
                    </tbody>
                </table>
                
                <h2 style="font-size: 22px; color: {COLOR_TEXTO}; margin-bottom: 15px;">🧠 Dirección de Arte & Conclusiones Estratégicas</h2>
                <div class="insights-card">
                    {insights_html}
                </div>
            </div>
        </body>
        </html>
        """
        with open("reporte.html", "w", encoding="utf-8") as f: f.write(html_final)
        with open("reporte.html", "rb") as file:
            st.download_button(f"📥 Descargar Reporte Velove ({total_marcas} Marcas)", data=file, file_name=f"Benchmark_Velove_{marca.replace(' ', '_')}.html", mime="text/html")
