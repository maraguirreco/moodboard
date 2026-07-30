import streamlit as st
from openai import OpenAI
import fitz  
import json
import requests
from duckduckgo_search import DDGS
import re
import base64
import urllib.parse
import time

# ==========================================
# CONFIGURACIÓN DE PÁGINA Y ESTADO
# ==========================================
st.set_page_config(page_title="Asistente de Dirección de Arte", layout="wide")

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
            Tu trabajo es DEDUCIR E INTERPRETAR los parámetros visuales strictly enfocados en DISEÑO, ignorando marketing o arquetipos.
            
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

def fetch_arena_images(query, limit=4):
    """Trae bloques de imagen de Are.na filtrando por calidad."""
    url = "https://api.are.na/v2/search/blocks"
    images = []
    try:
        response = requests.get(url, params={"q": query, "per": 20}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for block in data.get('blocks', []):
                if block.get('class') == 'Image' and 'image' in block and block['image'].get('display'):
                    img_url = block['image']['display']['url']
                    if img_url not in images:
                        images.append(img_url)
                    if len(images) >= limit:
                        break
    except Exception as e:
        print(f"Error en Are.na: {e}")
    return images

def fetch_design_web_images(query, google_api_key, google_cx, limit=4):
    """Busca imágenes EXCLUSIVAMENTE en tus sitios de elite vía Google Search API."""
    if not google_api_key or not google_cx:
        return []
        
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "cx": google_cx,
        "key": google_api_key,
        "searchType": "image",
        "num": limit,
        "safe": "off"
    }
    
    images = []
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            data = res.json()
            for item in data.get("items", []):
                images.append(item["link"])
        else:
            print(f"Google API Error {res.status_code}: {res.text}")
    except Exception as e:
        print(f"Error buscando en Google Custom Search para '{query}': {e}")
        
    return images

def fetch_unsplash_images(query, api_key, limit=4):
    """API Oficial de Unsplash para Fotografía y Moodboards."""
    if not api_key:
        return []
    url = "https://api.unsplash.com/search/photos"
    headers = {"Authorization": f"Client-ID {api_key}"}
    params = {"query": query, "per_page": limit, "orientation": "squarish"}
    images = []
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        if res.status_code == 200:
            for item in res.json().get('results', []):
                images.append(item['urls']['regular'])
    except Exception as e:
        print(f"Error en Unsplash: {e}")
    return images

def generate_search_queries(form_data, api_key):
    """Genera keywords estéticas y distribuye las búsquedas por especialidad."""
    client = OpenAI(base_url="[https://openrouter.ai/api/v1](https://openrouter.ai/api/v1)", api_key=api_key)
    
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
        # Aquí estaba el corte. Esta línea debe ir completa:
        raw_json = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        keywords = json.loads(raw_json)
    except Exception as e:
        print(f"Error generando keywords con IA: {e}")
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
