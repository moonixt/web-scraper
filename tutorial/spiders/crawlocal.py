from fileinput import filename
from pathlib import Path
from urllib import response
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin, urlparse

import scrapy
from tutorial.items import PageItem


class QuotesSpider(scrapy.Spider):
    name = "page"

    def __init__(self, katana_file=None, *args, **kwargs):
        super(QuotesSpider, self).__init__(*args, **kwargs)
        self.katana_file = katana_file
        
        # Extrair nome do arquivo sem extensão para organizar as imagens
        if katana_file:
            self.katana_filename = Path(katana_file).stem
        else:
            self.katana_filename = 'default'

    def start_requests(self):
        if not self.katana_file:
            self.logger.error("Arquivo katana_file é obrigatório!")
            return

        try:
            urls_set = set()  # Para evitar URLs duplicadas
            
            with open(self.katana_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        # Parse cada linha JSON
                        data = json.loads(line)
                        
                        # Extrair URL do formato Katana ou formato simples
                        url = None
                        if 'request' in data and 'endpoint' in data['request']:
                            # Formato original do Katana
                            url = data['request']['endpoint']
                        elif 'url' in data:
                            # Formato simplificado
                            url = data['url']
                            
                            # Filtrar apenas URLs principais (evitar assets JS/CSS)
                        
                        if url and self._is_main_page(url):
                            urls_set.add(url)
                                
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Erro ao decodificar linha {line_num}: {e}")
                        continue
            
            self.logger.info(f"Encontradas {len(urls_set)} URLs únicas")
            
            # Fazer requisições para as URLs
            for url in urls_set:
                yield scrapy.Request(url=url, callback=self.parse)
                
        except FileNotFoundError:
            self.logger.error(f"Arquivo não encontrado: {self.katana_file}")
        except Exception as e:
            self.logger.error(f"Erro ao processar arquivo: {e}")

    def _is_main_page(self, url):
        """Filtrar apenas páginas principais, ignorar assets"""
        # Ignora arquivos JavaScript, CSS, imagens, etc.
        ignore_extensions = ['.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2']
        
        for ext in ignore_extensions:
            if url.lower().endswith(ext):
                return False
        
        # Ignora URLs com certos padrões (assets, API, etc.)
        ignore_patterns = ['/_next/static/', '/api/', '/static/']
        
        for pattern in ignore_patterns:
            if pattern in url:
                return False
                
        return True

    def parse(self, response):
        # Criar pasta com base no nome do arquivo JSON
        if hasattr(self, 'katana_file') and self.katana_file:
            # Extrair nome do arquivo sem extensão
            json_filename = Path(self.katana_file).stem
            output_folder = Path(f"scraped_{json_filename}")
        else:
            # Fallback caso não tenha arquivo
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_folder = Path(f"scraped_pages_{timestamp}")
        
        output_folder.mkdir(exist_ok=True)
        
        # Extrair nome da página da URL
        url_parts = response.url.split('/')
        if url_parts[-1]:
            page_name = url_parts[-1].split('?')[0]  # Remove query params
        else:
            page_name = url_parts[-2] if len(url_parts) > 1 else 'index'
        
        # Limpar nome do arquivo
        page_name = page_name.replace('.', '_') if page_name else 'page'
        filename = output_folder / f"page-{page_name}.html"
        
        # Salvar HTML raw
        filename.write_bytes(response.body)
        self.log(f"Saved file {filename}")

        # Salvar HTML formatado
        soup = BeautifulSoup(response.body, "html.parser")
        pretty_html = soup.prettify()
        pretty_filename = output_folder / f"pretty-{page_name}.html"
        pretty_filename.write_text(pretty_html, encoding="utf-8")
        
        # Extrair URLs de imagens
        image_urls = []
        
        # Encontrar todas as tags img
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                # Converter URL relativa para absoluta
                full_url = urljoin(response.url, src)
                if self._is_valid_image_url(full_url):
                    image_urls.append(full_url)
        
        # Procurar por imagens em CSS background-image
        css_images = re.findall(r'background-image:\s*url\(["\']?([^"\'()]+)["\']?\)', response.text)
        for img_url in css_images:
            full_url = urljoin(response.url, img_url)
            if self._is_valid_image_url(full_url):
                image_urls.append(full_url)
        
        # Criar item com dados da página e imagens
        item = PageItem()
        item['title'] = soup.title.string if soup.title else page_name
        item['url'] = response.url
        item['content'] = response.text
        item['image_urls'] = list(set(image_urls)) if image_urls else []  # Remove duplicatas e garante lista
        item['images'] = []  # Inicializar campo para ImagesPipeline
        
        self.log(f"Encontradas {len(item['image_urls'])} imagens em {response.url}")
        if item['image_urls']:
            self.log(f"URLs de imagens: {item['image_urls']}")
        
        # Retornar item para pipeline processar as imagens
        yield item

    def _is_valid_image_url(self, url):
        """Verificar se é uma URL de imagem válida"""
        try:
            parsed = urlparse(url)
            # Verificar extensões de imagem
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
            path = parsed.path.lower()
            
            # Verificar se termina com extensão válida
            for ext in valid_extensions:
                if path.endswith(ext):
                    return True
            
            # Verificar se contém parâmetros de imagem (ex: Next.js images)
            if 'image' in parsed.path.lower() or 'img' in parsed.path.lower():
                return True
                
            return False
        except:
            return False