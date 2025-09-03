# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import os
import hashlib
from urllib.parse import urlparse
from scrapy.pipelines.images import ImagesPipeline
from scrapy.http import Request

# useful for handling different item types with a single interface
from itemadapter import ItemAdapter


class TutorialPipeline:
    def process_item(self, item, spider):
        return item


class CustomImagesPipeline(ImagesPipeline):
    """Pipeline customizado para organizar imagens por nome do arquivo JSON"""
    
    def file_path(self, request, response=None, info=None, *, item=None):
        """Customiza o caminho onde as imagens são salvas"""
        # Obter o nome do arquivo JSON do spider
        katana_filename = getattr(info.spider, 'katana_filename', 'default')
        
        # Gerar hash da URL para nome único
        image_guid = hashlib.sha1(request.url.encode()).hexdigest()
        
        # Extrair extensão da URL
        parsed_url = urlparse(request.url)
        path = parsed_url.path
        extension = os.path.splitext(path)[1].lower()
        
        # Se não há extensão, tentar detectar do content-type
        if not extension and response:
            content_type = response.headers.get('content-type', b'').decode()
            if 'jpeg' in content_type or 'jpg' in content_type:
                extension = '.jpg'
            elif 'png' in content_type:
                extension = '.png'
            elif 'gif' in content_type:
                extension = '.gif'
            elif 'webp' in content_type:
                extension = '.webp'
            else:
                extension = '.jpg'  # default
        elif not extension:
            extension = '.jpg'  # default
            
        # Retornar caminho: images/katana_filename/hash.ext
        return f'{katana_filename}/{image_guid}{extension}'
