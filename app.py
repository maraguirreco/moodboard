import streamlit as st
from openai import OpenAI
import fitz  
import json
import requests
from duckduckgo_search import DDGS
import re
import base64

# ==========================================
# CONFIGURACIÓN DE PÁGINA Y ESTADO
# ==========================================
st.set_page_config(page_title="Asistente de Dirección de Arte", layout="wide")

# Inicializamos el estado de la sesión para guardar los datos de la IA
if "form_data" not in st.session_state:
    st.session_state.form_data = {
        "industria": "", "personalidad": "", "resumen": "", "anti_referentes": "",
        "logo_estilo": "", "logo_referencias": "",
        "color_muestras": "", "color_temperatura": "", "color_luz": "",
        "tipo_clasificacion": "", "tipo_personalidad": "", "tipo_composicion": "",
        "formas_estructura": "", "formas_estilo": "", "formas_adicional": "",
        "img_sujetos": "", "img_metafora": "", "img_vibe": "", "img_encuadre": ""
    }

# ==========================================
# FUNCIONES DE PROCESAMIENTO
# ==========================================
def analyze_pdf_with_vision(pdf_file, api_key):
    """Convierte el PDF a imágenes y usa IA visual para leer el tablero de Miro."""
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    content_payload = [
        {
            "type": "text", 
            "text": """
            Eres un Director de Arte experto. Analiza las siguientes imágenes de una conceptualización de marca.
            Tu trabajo es DEDUCIR E INTERPRETAR los parámetros visuales estrictamente enfocados en DISEÑO, ignorando marketing o arquetipos.
            
            Responde ÚNICAMENTE con un objeto JSON válido con esta estructura exacta:
            {
                "industria": "string", "personalidad": "string", "resumen": "string", "anti_referentes": "string",
                "logo_estilo": "string", "logo_referencias": "string",
                "color_muestras": "string", "color_temperatura": "string", "color_luz": "string",
                "tipo_clasificacion": "string", "tipo_personalidad": "string", "tipo_composicion": "string",
                "formas_estructura": "string", "formas_estilo": "string", "formas_adicional": "string",
                "img_sujetos": "string", "img_metafora": "string", "img_vibe": "string", "img_encuadre": "string"
            }
            """
        }
    ]
    
    for i in range(min(len(doc), 3)):
        page = doc[i]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)) 
        base64_image = base64.b64encode(pix.tobytes("png")).decode('utf-8')
        content_payload.append({
            "type": "image_url", 
            "image_url": {"url": f"data:image/png;base64,{base64_image}"}
        })

    response = client.chat.completions.create(
        model="openai/gpt-4o-mini", 
        messages=[{"role": "user", "content": content_payload}]
    )
    
    raw_json = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
    return json.loads(raw_json)

import urllib.parse

def fetch_arena_images(query, limit=4):
    """Fortalece la búsqueda en Are.na trayendo más bloques por consulta y filtrando solo imágenes."""
    url = "https://api.are.na/v2/search/blocks"
    images = []
    try:
        # Pedimos 25 bloques (en vez de 10) para tener un margen de selección de imágenes de alta calidad
        response = requests.get(url, params={"q": query, "per": 25})
        if response.status_code == 200:
            data = response.json()
            for block in data.get('blocks', []):
                # Validamos que sea una imagen válida y tenga URL pública
                if block.get('class') == 'Image' and 'image' in block and block['image'].get('display'):
                    img_url = block['image']['display']['url']
                    if img_url not in images:
                        images.append(img_url)
                    if len(images) >= limit:
                        break
    except Exception as e:
        print(f"Error en Are.na: {e}")
    return images

def fetch_unsplash_images(query, api_key, limit=4):
    """API Oficial de Unsplash para Fotografía, Color y Moodboards sin bloqueos."""
    if not api_key:
        return []
    url = "https://api.unsplash.com/search/photos"
    headers = {"Authorization": f"Client-ID {api_key}"}
    params = {"query": query, "per_page": limit, "orientation": "squarish"}
    images = []
    try:
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            for item in res.json().get('results', []):
                images.append(item['urls']['regular'])
    except Exception as e:
        print(f"Error en Unsplash: {e}")
    return images

def fetch_brandnew_images(query, limit=4):
    """Busca casos de estudio e identidades visuales específicamente en Brand New (UnderConsideration)."""
    images = []
    # Usamos la búsqueda de DuckDuckGo restringida EXCLUSIVAMENTE a Brand New
    target_site = "site:underconsideration.com/brandnew"
    full_query = f"{query} {target_site}"
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(full_query, max_results=limit))
            for r in results:
                images.append(r['image'])
    except Exception as e:
        print(f"Error en Brand New: {e}")
    return images

def generate_search_queries(form_data, api_key):
    """Genera keywords estéticas y distribuye inteligentemente las búsquedas por especialidad."""
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    
    def clean_val(key):
        val = form_data.get(key, "")
        return str(val).strip() if val else ""
    
    prompt = f"""
    Eres un director de arte. Lee estos datos de diseño y devuelve SOLO 1 o 2 palabras clave en INGLÉS que definan la ESTÉTICA VISUAL. 
    PROHIBIDO usar sujetos (viajeros) o sentimientos (intelectual). USA SOLO términos gráficos (minimal, geometric, bold, warm, fluid).
    
    Datos:
    Logo: {clean_val('logo_estilo')}
    Colores: {clean_val('color_muestras')}
    Tipografía: {clean_val('tipo_clasificacion')}
    Formas: {clean_val('formas_estructura')}
    Imágenes: {clean_val('img_vibe')}
    
    Responde ÚNICAMENTE en JSON con la estructura:
    {{"logo": "str", "colores": "str", "tipografia": "str", "formas": "str", "imagenes": "str"}}
    """
    
    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        raw_json = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        keywords = json.loads(raw_json)
    except:
        keywords = {"logo": "minimal", "colores": "warm", "tipografia": "sans", "formas": "abstract", "imagenes": "editorial"}
        
    queries = {}
    sufijos = {
        "logo": "identity logo",
        "colores": "color palette",
        "tipografia": "typography layout",
        "formas": "graphic pattern",
        "imagenes": "photography"
    }
    
    for cat, sufijo in sufijos.items():
        base_kw = keywords.get(cat, "")
        if not isinstance(base_kw, str): base_kw = str(base_kw)
        base_kw = " ".join(base_kw.split()[:2])
        if not base_kw: base_kw = "design"
            
        queries[cat] = f"{base_kw} {sufijo}"
        
    return queries
# ==========================================
# INTERFAZ DE USUARIO (UI)
# ==========================================
st.title("🧠 Asistente de Dirección de Arte Automatizado")
st.markdown("Sube tu PDF de conceptualización y deja que la IA extraiga las pautas visuales.")

# --- BARRA LATERAL: API KEY ---
with st.sidebar:
    st.header("Configuración")
    
    # Intenta leer las claves secretas del servidor. Si no existen, muestra el campo de texto.
    gemini_api_key = st.secrets.get("OPENROUTER_API_KEY", "")
    if not gemini_api_key:
        gemini_api_key = st.text_input("API Key de OpenRouter:", type="password")
    else:
        st.success("✅ API de OpenRouter conectada")
        
    miro_token = st.secrets.get("MIRO_TOKEN", "")
    if not miro_token:
        miro_token = st.text_input("Access Token de Miro:", type="password")
        st.markdown("🔑 [Consigue tu Token de Miro aquí](https://miro.com/app/dashboard/)")
    else:
        st.success("✅ API de Miro conectada")

# --- CARGADOR DE PDF ---
uploaded_file = st.file_uploader("Subir PDF de conceptualización", type="pdf")

if uploaded_file is not None and st.button("✨ Analizar PDF con IA Visual"):
    if not gemini_api_key:
        st.error("Por favor ingresa tu API Key en la barra lateral.")
    else:
        with st.spinner("👀 La IA está 'leyendo' visualmente tu documento de Miro..."):
            try:
                # Extraemos los datos visualmente
                extracted_data = analyze_pdf_with_vision(uploaded_file, gemini_api_key)
                
                # Inyectamos los datos en la memoria de la aplicación
                st.session_state.form_data.update(extracted_data)
                
                # Forzamos a que la pantalla parpadee y rellene todas las casillas
                st.rerun()
                
            except Exception as e:
                st.error(f"Hubo un error al procesar el archivo: {e}")

# --- FORMULARIO DE PAUTAS VISUALES ---
st.header("1. Contexto Estratégico")
col1, col2 = st.columns(2)
with col1:
    industria = st.text_input("Industria / Sector", value=st.session_state.form_data.get("industria", ""))
    personalidad = st.text_input("Atributos de Personalidad (separados por coma)", value=st.session_state.form_data.get("personalidad", ""))
with col2:
    anti_referentes = st.text_input("Lo que NO queremos (Anti-referentes)", value=st.session_state.form_data.get("anti_referentes", ""))
    resumen = st.text_area("Resumen del partido conceptual", value=st.session_state.form_data.get("resumen", ""))

st.header("2. Casillas por Categoría Visual")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Logotipo", "Colores", "Tipografía", "Formas", "Imágenes"])

# Data guardada en variables temporales para evitar errores de selectbox
d = st.session_state.form_data

with tab1:
    st.subheader("LOGOTIPO (Identidad y Símbolo)")
    st.session_state.form_data['logo_estilo'] = st.text_input("Estilo del Símbolo", value=st.session_state.form_data.get("logo_estilo", ""), placeholder="Ej: Minimalista, orgánico, line art, isotipo geométrico...")
    st.session_state.form_data['logo_referencias'] = st.text_input("Marcas o Sectores de Referencia", value=st.session_state.form_data.get("logo_referencias", ""), placeholder="Ej: Símbolos de conexión, escudos, tecnología limpia...")

with tab2:
    st.subheader("COLORES (Paleta & Atmósfera de Luz)")
    st.session_state.form_data['color_muestras'] = st.text_input("Colores Clave & Acentos", value=st.session_state.form_data.get("color_muestras", ""), placeholder="Ej: Verde suave, azul claro, tonos tierra...")
    st.session_state.form_data['color_temperatura'] = st.text_input("Temperatura & Saturación", value=st.session_state.form_data.get("color_temperatura", ""), placeholder="Ej: Cálido y acogedor, frío y corporativo, desaturado...")
    st.session_state.form_data['color_luz'] = st.text_input("Dirección de Iluminación", value=st.session_state.form_data.get("color_luz", ""), placeholder="Ej: Luminoso y natural, claroscuro dramático...")

with tab3:
    st.subheader("TIPO (Estilo Tipográfico)")
    st.session_state.form_data['tipo_clasificacion'] = st.text_input("Clasificación Tipográfica", value=st.session_state.form_data.get("tipo_clasificacion", ""), placeholder="Ej: Serif, sans serif, geométrica, display...")
    st.session_state.form_data['tipo_personalidad'] = st.text_input("Personalidad", value=st.session_state.form_data.get("tipo_personalidad", ""), placeholder="Ej: Ligero y accesible, elegante, técnico, ruidoso...")
    st.session_state.form_data['tipo_composicion'] = st.text_input("Composición / Layout Tipográfico", value=st.session_state.form_data.get("tipo_composicion", ""), placeholder="Ej: Editorial limpio, tipografía suiza, brutalista, big typography...")

with tab4:
    st.subheader("FORMAS (Recursos Gráficos)")
    st.session_state.form_data['formas_estructura'] = st.text_input("La Forma y la Estructura", value=st.session_state.form_data.get("formas_estructura", ""), placeholder="Ej: Organic shapes, fluid forms, abstract geometry, smooth curves...")
    st.session_state.form_data['formas_estilo'] = st.text_input("Estilo de Referencia o 'Vibe'", value=st.session_state.form_data.get("formas_estilo", ""), placeholder="Ej: Aesthetic, clean layout, modern branding, flat design...")
    st.session_state.form_data['formas_adicional'] = st.text_input("Información Adicional", value=st.session_state.form_data.get("formas_adicional", ""), placeholder="Ej: Sellos, stickers, texturas granuladas, líneas finas...")

with tab5:
    st.subheader("IMÁGENES")
    st.session_state.form_data['img_sujetos'] = st.text_input("Sujetos u Objetos Clave", value=st.session_state.form_data.get("img_sujetos", ""), placeholder="Ej: Viajeros y culturas diversas, objetos cotidianos...")
    st.session_state.form_data['img_metafora'] = st.text_input("Metáfora Visual / Concepto", value=st.session_state.form_data.get("img_metafora", ""), placeholder="Ej: Puentes y conexiones, crecimiento, transparencia...")
    st.session_state.form_data['img_vibe'] = st.text_input("Vibe / Atmósfera Emocional", value=st.session_state.form_data.get("img_vibe", ""), placeholder="Ej: Introspectivo y reflexivo, dinámico e innovador, nostálgico...")
    st.session_state.form_data['img_encuadre'] = st.text_input("Encuadre Fotográfico Dominante", value=st.session_state.form_data.get("img_encuadre", ""), placeholder="Ej: Amplio incluyendo paisajes, primer plano detalle, macro...")
    
# --- BOTÓN FINAL: GENERAR Y BUSCAR MOODBOARDS ---
with st.spinner("🚀 Ejecutando búsqueda especializada en Brand New, Are.na y Unsplash..."):
            import time
            unsplash_key = st.secrets.get("UNSPLASH_ACCESS_KEY", "")
            resultados_visuales = {}
            
            for categoria, query_texto in st.session_state.queries.items():
                img_arena = []
                img_web = []
                
                # ESTRATEGIA MULTI-MOTOR SEGÚN LA CATEGORÍA VISUAL:
                if categoria == "logo":
                    # Brand New es el rey absoluto en Logotipos e Identidad
                    img_web = fetch_brandnew_images(query_texto, limit=4)
                    img_arena = fetch_arena_images(query_texto, limit=4)
                    
                elif categoria in ["tipografia", "formas"]:
                    # Are.na es la mejor para Tipografía, Diagramación y Patrones Gráficos
                    img_arena = fetch_arena_images(query_texto, limit=4)
                    # Apoyo de Unsplash/BrandNew
                    img_web = fetch_unsplash_images(query_texto, unsplash_key, limit=4)
                    
                else: # colores e imágenes
                    # Unsplash es imbatible en Fotografía, Atmósferas y Paletas cromáticas
                    img_web = fetch_unsplash_images(query_texto, unsplash_key, limit=4)
                    img_arena = fetch_arena_images(query_texto, limit=4)
                
                # Pausa ligera de seguridad
                time.sleep(1)
                
                resultados_visuales[categoria] = {
                    "arena": img_arena,
                    "web": img_web
                }
            
            st.success("¡Moodboard profesional generado exitosamente!")
            
            # --- RENDERIZADO VISUAL EN PANTALLA ---
            st.write("## 🎨 Resultados del Moodboard")
            
            for categoria, imagenes in resultados_visuales.items():
                st.write(f"### {categoria.upper()}")
                
                # --- MODO DIAGNÓSTICO: Ver qué buscó la IA ---
                datos_busqueda = st.session_state.queries[categoria]
                st.caption(f"🔍 **Are.na:** `{datos_busqueda.get('arena_query', '')}`")
                st.caption(f"🔍 **Web:** `{datos_busqueda.get('web_query', '')}`")
                
                if not imagenes['arena'] and not imagenes['web']:
                    st.warning("⚠️ Los buscadores no encontraron nada con estos términos o bloquearon la conexión.")
                
                if imagenes['arena']:
                    st.caption("🟢 Extraído de Are.na")
                    cols = st.columns(len(imagenes['arena']))
                    for idx, img_url in enumerate(imagenes['arena']):
                        with cols[idx]:
                            st.image(img_url, use_column_width=True)
                
                if imagenes['web']:
                    st.caption("🌐 Extraído de Web")
                    cols = st.columns(len(imagenes['web']))
                    for idx, img_url in enumerate(imagenes['web']):
                        with cols[idx]:
                            st.image(img_url, use_column_width=True)
                st.divider()

            # --- VOLCADO A MIRO ---
            st.write("## 🚀 Exportación a Miro")
            
            if not miro_token:
                st.warning("⚠️ Agrega tu Access Token de Miro en la barra lateral para crear el tablero automáticamente.")
            else:
                with st.spinner("Conectando con Miro y organizando las imágenes en Frames... (Esto puede tomar un minuto)"):
                    nombre_tablero = st.session_state.form_data.get('industria', 'Nueva Marca')
                    miro_url, error = export_to_miro(resultados_visuales, miro_token, nombre_proyecto=nombre_tablero)
                    
                    if error:
                        st.error(error)
                    else:
                        st.success("¡Tablero creado con éxito!")
                        st.markdown(f"### 🎉 [Haz clic aquí para abrir tu Moodboard en Miro]({miro_url})")
