import streamlit as st
from openai import OpenAI
import PyPDF2
import json
import re

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
def extract_text_from_pdf(pdf_file):
    """Extrae el texto de un archivo PDF subido."""
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def analyze_with_gemini(text, api_key):
    """Envía el texto a Gemini para extraer los parámetros de diseño."""
    genai.configure(api_key=api_key)
    
    # Usamos Gemini 1.5 Flash que es rapidísimo y muy bueno estructurando JSON
    model = genai.GenerativeModel('gemini-1.5-flash') 
    
    prompt = f"""
    Eres un Director de Arte experto. Analiza el siguiente documento de conceptualización de marca y extrae los parámetros visuales solicitados.
    Si el documento no menciona algo, déjalo en blanco (""). 
    
    Responde ÚNICAMENTE con un objeto JSON válido con esta estructura exacta (no agregues markdown ni texto adicional):
    {{
        "industria": "string",
        "personalidad": "string (separado por comas)",
        "resumen": "string",
        "anti_referentes": "string (separado por comas)",
        "logo_estilo": "string",
        "logo_arquetipo": ["array de strings"],
        "logo_referencias": "string",
        "color_muestras": "string (ej: terracota, arena)",
        "color_temperatura": "string",
        "color_luz": "string",
        "tipo_clasificacion": ["array de strings"],
        "tipo_peso": "string",
        "tipo_muestra": "string",
        "formas_bordes": "string",
        "formas_elementos": ["array de strings"],
        "formas_layout": "string",
        "img_sujetos": "string",
        "img_metafora": "string",
        "img_vibe": ["array de strings"],
        "img_encuadre": "string"
    }}
    
    Texto a analizar:
    {text}
    """
    
    response = model.generate_content(prompt)
    
    # Limpiamos la respuesta en caso de que la IA incluya bloques de código ```json
    raw_json = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(raw_json)
def generate_search_queries(form_data, api_key):
    """Toma los datos del formulario y genera queries de búsqueda en inglés estructurados."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Preparamos la lista de sitios de alta calidad para el operador site:
    sites = "site:brandarchive.xyz OR site:thedieline.com OR site:awwwards.com OR site:itsnicethat.com OR site:siteinspire.com OR site:designspiration.com OR site:cosmos.so"
    
    prompt = f"""
    Eres un curador de diseño gráfico experto. Toma los siguientes parámetros en español de una identidad de marca y tradúcelos a palabras clave (queries) altamente específicas en INGLÉS para buscar referentes visuales.
    
    Contexto de la marca:
    - Industria: {form_data.get('industria')}
    - Personalidad: {form_data.get('personalidad')}
    - Anti-referentes: {form_data.get('anti_referentes')} (Conviértelos en palabras clave negativas en inglés, usando un guión antes de la palabra, ej: -neon -3d -corporate)
    
    Parámetros por categoría:
    - Logo: {form_data.get('logo_estilo')}, {form_data.get('logo_arquetipo')}
    - Colores: {form_data.get('color_muestras')}, {form_data.get('color_temperatura')}
    - Tipografía: {form_data.get('tipo_clasificacion')}, {form_data.get('tipo_peso')}
    - Formas: {form_data.get('formas_bordes')}, {form_data.get('formas_elementos')}
    - Imágenes: {form_data.get('img_sujetos')}, {form_data.get('img_vibe')}
    
    Instrucciones:
    Para cada una de las 5 categorías (logo, colores, tipografia, formas, imagenes), genera 2 tipos de queries:
    1. 'arena_query': Palabras clave estéticas en inglés separadas por espacio.
    2. 'web_query': Las mismas palabras clave, pero agregando al final los anti-referentes (ej: -cheap) y esta cadena exacta de sitios: {sites}
    
    Responde ÚNICAMENTE con un JSON válido con esta estructura exacta:
    {{
        "logo": {{"arena_query": "string", "web_query": "string"}},
        "colores": {{"arena_query": "string", "web_query": "string"}},
        "tipografia": {{"arena_query": "string", "web_query": "string"}},
        "formas": {{"arena_query": "string", "web_query": "string"}},
        "imagenes": {{"arena_query": "string", "web_query": "string"}}
    }}
    """
    
    response = model.generate_content(prompt)
    raw_json = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(raw_json)
# ==========================================
# INTERFAZ DE USUARIO (UI)
# ==========================================
st.title("🧠 Asistente de Dirección de Arte Automatizado")
st.markdown("Sube tu PDF de conceptualización y deja que la IA extraiga las pautas visuales.")

# --- BARRA LATERAL: API KEY ---
with st.sidebar:
    st.header("Configuración")
    gemini_api_key = st.text_input("Ingresa tu Gemini API Key:", type="password")
    st.markdown("[Consigue tu API Key gratis aquí](https://aistudio.google.com/app/apikey)")

# --- CARGADOR DE PDF ---
uploaded_file = st.file_uploader("Subir PDF de conceptualización", type="pdf")

if uploaded_file is not None and st.button("✨ Analizar PDF con IA"):
    if not gemini_api_key:
        st.error("Por favor ingresa tu API Key de Gemini en la barra lateral.")
    else:
        with st.spinner("Analizando el documento y extrayendo pautas visuales..."):
            try:
                pdf_text = extract_text_from_pdf(uploaded_file)
                extracted_data = analyze_with_gemini(pdf_text, gemini_api_key)
                
                # Actualizamos el estado de la sesión con los datos de la IA
                # Esto auto-completará los campos abajo
                st.session_state.form_data.update(extracted_data)
                st.success("¡Análisis completado! Revisa y ajusta los campos abajo.")
            except Exception as e:
                st.error(f"Hubo un error al procesar: {e}")

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

# --- BOTÓN FINAL: GENERAR QUERIES ---
st.divider()
if st.button("🚀 Generar Moodboards (Fase 2)"):
    if not gemini_api_key:
        st.error("Por favor ingresa tu API Key de Gemini en la barra lateral.")
    else:
        with st.spinner("🧠 Traduciendo tu concepto a código de búsqueda profesional..."):
            try:
                # 1. Llamamos a la función para generar los queries
                queries = generate_search_queries(st.session_state.form_data, gemini_api_key)
                
                # 2. Mostramos los resultados en la interfaz para que los veas
                st.success("¡Queries generados con éxito!")
                
                st.write("### 🔍 Así buscará la app en internet:")
                
                # Usamos expanders de Streamlit para mostrarlo ordenado
                for categoria, datos in queries.items():
                    with st.expander(f"Categoria: {categoria.upper()}"):
                        st.markdown(f"**🟢 Búsqueda en Are.na:** `{datos['arena_query']}`")
                        st.markdown(f"**🌐 Búsqueda en Web (Nicho):** `{datos['web_query']}`")
                
                # Guardamos los queries en el estado para la siguiente fase
                st.session_state.queries = queries
                
            except Exception as e:
                st.error(f"Hubo un error al generar los queries: {e}")
