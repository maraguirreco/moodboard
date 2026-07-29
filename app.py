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
        "logo_estilo": "", "logo_arquetipo": [], "logo_referencias": "",
        "color_muestras": "", "color_temperatura": "", "color_luz": "",
        "tipo_clasificacion": [], "tipo_peso": "", "tipo_muestra": "",
        "formas_bordes": "", "formas_elementos": [], "formas_layout": "",
        "img_sujetos": "", "img_metafora": "", "img_vibe": [], "img_encuadre": ""
    }

# ==========================================
# FUNCIONES DE PROCESAMIENTO
# ==========================================
def analyze_pdf_with_vision(pdf_file, api_key):
    """Convierte el PDF a imágenes y usa IA visual para leer el tablero de Miro sin importar si está en curvas."""
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    content_payload = [
        {
            "type": "text", 
            "text": """
            Eres un Director de Arte experto. Analiza las siguientes imágenes de una conceptualización de marca (mapas mentales, diagramas, textos sueltos).
            Tu trabajo es DEDUCIR E INTERPRETAR los parámetros visuales a partir de los conceptos que leas. 
            Ejemplo: Si lees "Turismo consciente", deduce que la industria es "Turismo". Si ves colores en la imagen, descríbelos.
            No seas literal, interpreta el mood y la esencia del documento.
            
            Responde ÚNICAMENTE con un objeto JSON válido con esta estructura exacta:
            {
                "industria": "string", "personalidad": "string", "resumen": "string", "anti_referentes": "string",
                "logo_estilo": "string", "logo_arquetipo": "string", "logo_referencias": "string",
                "color_muestras": "string", "color_temperatura": "string", "color_luz": "string",
                "tipo_clasificacion": "string", "tipo_peso": "string", "tipo_muestra": "string",
                "formas_bordes": "string", "formas_elementos": "string", "formas_layout": "string",
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


def generate_search_queries(form_data, api_key):
    """Genera queries en inglés usando OpenRouter."""
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    sites = "site:brandarchive.xyz OR site:thedieline.com OR site:awwwards.com OR site:itsnicethat.com OR site:siteinspire.com OR site:designspiration.com OR site:cosmos.so"
    
    prompt = f"""
    Eres un curador de diseño experto. Traduce estos parámetros a palabras clave en INGLÉS para buscar referentes.
    Industria: {form_data.get('industria')} | Anti-referentes: {form_data.get('anti_referentes')} (usa -palabra)
    Logo: {form_data.get('logo_estilo')}, {form_data.get('logo_arquetipo')}
    Colores: {form_data.get('color_muestras')}, {form_data.get('color_temperatura')}
    Tipografía: {form_data.get('tipo_clasificacion')}, {form_data.get('tipo_peso')}
    Formas: {form_data.get('formas_bordes')}, {form_data.get('formas_elementos')}
    Imágenes: {form_data.get('img_sujetos')}, {form_data.get('img_vibe')}
    
    Para cada categoría (logo, colores, tipografia, formas, imagenes), genera:
    1. 'arena_query': Palabras clave estéticas separadas por espacio.
    2. 'web_query': Palabras clave + anti-referentes + la cadena: {sites}
    
    Responde ÚNICAMENTE en JSON con la estructura:
    {{"logo": {{"arena_query": "str", "web_query": "str"}}, "colores": {{"arena_query": "str", "web_query": "str"}}, "tipografia": {{"arena_query": "str", "web_query": "str"}}, "formas": {{"arena_query": "str", "web_query": "str"}}, "imagenes": {{"arena_query": "str", "web_query": "str"}}}}
    """
    
    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    raw_json = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
    return json.loads(raw_json)

def fetch_arena_images(query, limit=4):
    """Busca en la API pública de Are.na y devuelve URLs de imágenes."""
    url = f"https://api.are.na/v2/search/blocks?q={query}&per=10"
    images = []
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            for block in data.get('blocks', []):
                if block.get('class') == 'Image' and 'image' in block:
                    images.append(block['image']['display']['url'])
                    if len(images) >= limit:
                        break
    except Exception as e:
        print(f"Error en Are.na: {e}")
    return images

def fetch_ddg_images(query, limit=4):
    """Busca imágenes en la web (usando tus sitios nicho) vía DuckDuckGo."""
    images = []
    try:
        results = DDGS().images(query, max_results=limit)
        for r in results:
            images.append(r['image'])
    except Exception as e:
        print(f"Error en DuckDuckGo: {e}")
    return images
def export_to_miro(resultados_visuales, miro_token, nombre_proyecto="Mi Moodboard"):
    """Crea un tablero en Miro con formato de Tabla dinámica estructurada y colores corporativos."""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {miro_token}"
    }
    
    # 1. Crear Tablero
    board_url = "https://api.miro.com/v2/boards"
    board_payload = {"name": f"Moodboard: {nombre_proyecto}"}
    board_res = requests.post(board_url, json=board_payload, headers=headers).json()
    board_id = board_res.get('id')
    board_view_url = board_res.get('viewLink')
    
    if not board_id:
        return None, f"Error creando el tablero: {board_res}"

    # 2. Configuración de la "Tabla"
    categorias = ["logo", "colores", "tipografia", "formas", "imagenes"]
    titulos = ["Logotipo", "Colores", "Tipografía", "Formas", "Imágenes"]
    
    # Tus colores corporativos
    color_azul = "#050038"
    color_fondo = "#F8F6F2"
    color_casilla = "#FFFFFF"
    
    ancho_columna = 500
    alto_imagen = 400
    margen = 50
    
    # Calcular el alto dinámico basado en la columna con más imágenes
    max_imagenes = max([len(resultados_visuales.get(cat, {}).get('arena', []) + resultados_visuales.get(cat, {}).get('web', [])) for cat in categorias])
    
    # Si por alguna razón no hay imágenes, damos un alto mínimo
    if max_imagenes == 0: max_imagenes = 1 
    
    alto_frame = (max_imagenes * (alto_imagen + margen)) + 250 # Espacio extra para la cabecera
    ancho_frame = (len(categorias) * ancho_columna)
    
    # 3. Crear el Gran Frame Contenedor (El fondo gris de la tabla)
    frame_payload = {
        "data": {"title": f"Moodboard Estructurado - {nombre_proyecto}"},
        "style": {"fillColor": color_fondo}, # <-- Aquí inyectamos el gris #F8F6F2
        "position": {"x": ancho_frame / 2, "y": alto_frame / 2},
        "geometry": {"width": ancho_frame, "height": alto_frame}
    }
    frame_res = requests.post(f"{board_url}/{board_id}/frames", json=frame_payload, headers=headers).json()
    frame_id = frame_res.get('id')
    
    # 4. Dibujar las Columnas, Cabeceras e Imágenes
    for col_idx, cat in enumerate(categorias):
        # Posición base en X para esta columna (relativa al centro del frame)
        col_x = (col_idx * ancho_columna) - (ancho_frame / 2) + (ancho_columna / 2)
        
        # Dibujar rectángulos blancos con texto azul (Cabeceras)
        shape_payload = {
            "data": {
                "shape": "rectangle",
                # <-- El texto va en tu azul corporativo #050038
                "content": f"<p><span style='color: {color_azul}; font-family: sans-serif; font-size: 24px;'><strong>{titulos[col_idx]}</strong></span></p>"
            },
            "style": {
                "fillColor": color_casilla,      # <-- La casilla en blanco
                "borderColor": color_azul,       # <-- Borde azul para enmarcar
                "borderStyle": "normal",
                "textAlign": "center"
            },
            "position": {"x": col_x, "y": -(alto_frame / 2) + 100},
            "geometry": {"width": ancho_columna - 40, "height": 80},
            "parent": {"id": frame_id}
        }
        requests.post(f"{board_url}/{board_id}/shapes", json=shape_payload, headers=headers)
        
        # Obtener y acomodar las imágenes verticalmente en esta columna
        todas_las_imagenes = resultados_visuales.get(cat, {}).get('arena', []) + resultados_visuales.get(cat, {}).get('web', [])
        
        for row_idx, img_url in enumerate(todas_las_imagenes):
            img_y = -(alto_frame / 2) + 220 + (row_idx * (alto_imagen + margen)) + (alto_imagen / 2)
            
            img_payload = {
                "data": {"url": img_url},
                "parent": {"id": frame_id},
                "position": {"x": col_x, "y": img_y},
                "geometry": {"width": ancho_columna - 40} # Dejamos 40px de respiro (márgenes)
            }
            requests.post(f"{board_url}/{board_id}/images", json=img_payload, headers=headers)
            
    return board_view_url, None
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
    logo_estilo = st.text_input("Estilo del Símbolo", value=d.get("logo_estilo", ""), placeholder="Ej: Line art, Isotipo geométrico...")
    logo_arquetipo = st.multiselect("Arquetipo Visual Primario", 
                                    options=["Sabio", "Creador", "Explorador", "Gobernante", "Cuidador", "Rebelde", "Mago", "Héroe", "Amante", "Bufón", "Hombre Corriente", "Inocente"],
                                    default=[a for a in d.get("logo_arquetipo", []) if a in ["Sabio", "Creador", "Explorador", "Gobernante", "Cuidador", "Rebelde", "Mago", "Héroe", "Amante", "Bufón", "Hombre Corriente", "Inocente"]])
    logo_referencias = st.text_input("Marcas o Sectores de Referencia", value=d.get("logo_referencias", ""))

with tab2:
    st.subheader("COLORES (Paleta & Atmósfera de Luz)")
    color_muestras = st.text_input("Colores Clave & Acentos", value=d.get("color_muestras", ""), placeholder="Ej: Azul marino profundo, acentos dorados...")
    color_temperatura = st.text_input("Temperatura & Saturación", value=d.get("color_temperatura", ""), placeholder="Ej: Cálido y terroso, Frío y corporativo...")
    color_luz = st.text_input("Dirección de Iluminación", value=d.get("color_luz", ""), placeholder="Ej: Luz natural suave, Claroscuro dramático...")

with tab3:
    st.subheader("TIPO (Estilo Tipográfico)")
    tipo_clasificacion = st.multiselect("Clasificación Tipográfica", 
                                        options=["Sans Serif Geométrica", "Sans Serif Humanista", "Serif Clásica", "Monospaced", "Display / Expresiva"],
                                        default=[t for t in d.get("tipo_clasificacion", []) if t in ["Sans Serif Geométrica", "Sans Serif Humanista", "Serif Clásica", "Monospaced", "Display / Expresiva"]])
    tipo_peso = st.text_input("Peso y Personalidad", value=d.get("tipo_peso", ""))
    tipo_muestra = st.text_input("Formato de Muestra Visual", value=d.get("tipo_muestra", ""))

with tab4:
    st.subheader("FORMAS (Recursos Gráficos y Layout)")
    formas_bordes = st.text_input("Tratamiento de Bordes", value=d.get("formas_bordes", ""))
    formas_elementos = st.multiselect("Elementos Gráficos Complementarios", 
                                      options=["Tickets/Stickers", "Sellos y badges", "Retículas técnicas", "Capas de papel", "Marcos de foto", "Capas geológicas", "Anillos/Arcos"],
                                      default=[f for f in d.get("formas_elementos", []) if f in ["Tickets/Stickers", "Sellos y badges", "Retículas técnicas", "Capas de papel", "Marcos de foto", "Capas geológicas", "Anillos/Arcos"]])
    formas_layout = st.text_input("Estilo de Composición (Layout)", value=d.get("formas_layout", ""))

with tab5:
    st.subheader("IMÁGENES (Fotografía y Estilo de Vida)")
    img_sujetos = st.text_input("Sujetos u Objetos Clave", value=d.get("img_sujetos", ""))
    img_metafora = st.text_input("Metáfora Visual / Concepto 'Hero'", value=d.get("img_metafora", ""))
    img_vibe = st.multiselect("Vibe / Atmósfera Emocional", 
                              options=["Introspectivo y reflexivo", "Dinámico e innovador", "Solemne e institucional", "Cálido y acogedor", "Audaz"],
                              default=[v for v in d.get("img_vibe", []) if v in ["Introspectivo y reflexivo", "Dinámico e innovador", "Solemne e institucional", "Cálido y acogedor", "Audaz"]])
    img_encuadre = st.text_input("Encuadre Fotográfico Dominante", value=d.get("img_encuadre", ""))

# --- BOTÓN FINAL: GENERAR Y BUSCAR MOODBOARDS ---
st.divider()
if st.button("🚀 Generar y Buscar Moodboards"):
    if not gemini_api_key:
        st.error("Por favor ingresa tu API Key de OpenRouter en la barra lateral.")
    else:
        with st.spinner("🧠 1/2: Traduciendo tu concepto a código de búsqueda profesional..."):
            try:
                queries = generate_search_queries(st.session_state.form_data, gemini_api_key)
                st.session_state.queries = queries
            except Exception as e:
                st.error(f"Hubo un error al generar los queries: {e}")
                st.stop()
                
        with st.spinner("🌐 2/2: Escaneando Are.na y sitios de nicho para extraer imágenes..."):
            resultados_visuales = {}
            
            for categoria, datos in st.session_state.queries.items():
                img_arena = fetch_arena_images(datos['arena_query'], limit=4)
                img_web = fetch_ddg_images(datos['web_query'], limit=4)
                
                resultados_visuales[categoria] = {
                    "arena": img_arena,
                    "web": img_web
                }
            
            st.success("¡Moodboards recopilados con éxito!")
            
            # --- RENDERIZADO VISUAL EN PANTALLA ---
            st.write("## 🎨 Resultados del Moodboard")
            
            for categoria, imagenes in resultados_visuales.items():
                st.write(f"### {categoria.upper()}")
                
                if imagenes['arena']:
                    st.caption("🟢 Extraído de Are.na")
                    cols = st.columns(len(imagenes['arena']))
                    for idx, img_url in enumerate(imagenes['arena']):
                        with cols[idx]:
                            st.image(img_url, use_column_width=True)
                
                if imagenes['web']:
                    st.caption("🌐 Extraído de TheDieline, BrandArchive, Cosmos, etc.")
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
