"""
core/web_crawler.py
Módulo de rastreo inteligente de contenido web para Atlas v3.9.
Permite la ingesta recursiva de sitios web basada en un tema, 
con clasificación automática de subcarpetas y filtrado semántico.
"""
import os
import requests
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from core.brain import pensar_sin_streaming
from core.local_ingestion_manager import crear_subcarpeta
from core.digestion_worker import digerir_documento

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebCrawler:
    def __init__(self, root_folder, theme, max_pages=20):
        self.root_folder = root_folder
        self.theme = theme
        self.max_pages = max_pages
        self.visited = set()
        self.queue = []
        self.processed_count = 0

    def _is_relevant(self, text):
        """
        Usa el cerebro de Atlas para determinar si el contenido es relevante para el tema.
        """
        prompt = f\"\"\"
        Analiza el siguiente fragmento de texto y determina si es relevante para el tema: '{self.theme}'.
        Responde ÚNICAMENTE con 'SÍ' o 'NO'.
        
        Texto:
        {text[:2000]}
        \"\"\"
        try:
            # Usamos el motor más rápido (Groq) para el filtrado masivo
            res = pensar_sin_streaming(prompt, motor="groq").strip().upper()
            return "SÍ" in res
        except Exception as e:
            logger.error(f"Error en filtrado de relevancia: {e}")
            return True # En caso de error, dejamos pasar para no perder info

    def _get_subfolder_name(self, text):
        """
        Usa el cerebro de Atlas para sugerir una subcarpeta basada en el contenido.
        """
        prompt = f\"\"\"
        Basado en el siguiente texto, sugiere un nombre corto (1-3 palabras) para una carpeta que categorice este contenido dentro del tema '{self.theme}'.
        El nombre debe ser simple, sin espacios (usa guiones bajos) y en minúsculas.
        Responde ÚNICAMENTE con el nombre de la carpeta.
        
        Texto:
        {text[:2000]}
        \"\"\"
        try:
            res = pensar_sin_streaming(prompt, motor="groq").strip().lower()
            # Limpiar cualquier carácter no deseado
            return "".join(c for c in res if c.isalnum() or c == '_')
        except Exception as e:
            logger.error(f"Error sugiriendo subcarpeta: {e}")
            return "general"

    def _extract_links(self, soup, base_url):
        """Extrae links internos del sitio."""
        links = set()
        for a in soup.find_all('a', href=True):
            url = urljoin(base_url, a['href'])
            # Solo links del mismo dominio
            if urlparse(base_url).netloc == urlparse(url).netloc:
                # Evitar anclas y archivos no textuales
                if not url.split('#')[0].endswith(('.pdf', '.jpg', '.png', '.zip', '.exe')):
                    links.add(url.split('#')[0])
        return links

    def crawl(self, start_url):
        """
        Inicia el proceso de rastreo y digestión.
        Retorna un generador de progreso.
        """
        self.queue.append(start_url)
        
        while self.queue and self.processed_count < self.max_pages:
            url = self.queue.pop(0)
            if url in self.visited:
                continue
            
            self.visited.add(url)
            logger.info(f"Rastreando: {url}")
            
            try:
                resp = requests.get(url, timeout=10, headers={'User-Agent': 'AtlasBot/3.9'})
                if resp.status_code != 200:
                    continue
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # 1. Limpiar HTML (quitar scripts, estilos, navs)
                for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                    tag.decompose()
                
                texto_limpio = soup.get_text(separator=" ", strip=True)
                
                if not texto_limpio or len(texto_limpio) < 200:
                    continue

                # 2. Filtrar Relevancia
                if not self._is_relevant(texto_limpio):
                    yield {"estado": "info", "mensaje": f"⏩ Saltando página no relevante: {url}"}
                    continue
                
                # 3. Determinar Subcarpeta
                subfolder = self._get_subfolder_name(texto_limpio)
                full_path = os.path.join(self.root_folder, subfolder)
                
                # Crear carpeta si no existe
                crear_subcarpeta(full_path)
                
                # 4. Digerir y Guardar
                nombre_archivo = urlparse(url).path.replace('/', '_').strip('_') or "index"
                nombre_final = f"{nombre_archivo}.md"
                
                # Usamos el worker de digestión existente
                texto_digerido = digerir_documento(
                    texto_crudo=texto_limpio,
                    nombre_original=nombre_final,
                    url_origen=url,
                    motor="groq" # Usamos Groq para velocidad en el crawler
                )
                
                # Guardar el archivo físicamente
                with open(os.path.join(full_path, nombre_final), "w", encoding="utf-8") as f:
                    f.write(f"# Fuente: {url}\\n\\n{texto_digerido}")
                
                self.processed_count += 1
                yield {
                    "estado": "completado", 
                    "mensaje": f"✅ Indexado en {subfolder}: {nombre_final}",
                    "progreso": (self.processed_count / self.max_pages) * 100
                }
                
                # 5. Agregar nuevos links a la cola
                nuevos_links = self._extract_links(soup, url)
                self.queue.extend(list(nuevos_links - self.visited))
                
            except Exception as e:
                logger.error(f"Error procesando {url}: {e}")
                yield {"estado": "error", "mensaje": f"❌ Error en {url}: {str(e)}"}

        yield {"estado": "finalizado", "mensaje": f"🏁 Rastreo completado. {self.processed_count} páginas indexadas."}
