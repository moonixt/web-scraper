# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class TutorialItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


class PageItem(scrapy.Item):
    # Dados da página
    title = scrapy.Field()
    url = scrapy.Field()
    content = scrapy.Field()
    
    # URLs das imagens encontradas
    image_urls = scrapy.Field()
    
    # Caminhos das imagens baixadas (preenchido automaticamente)
    images = scrapy.Field()
