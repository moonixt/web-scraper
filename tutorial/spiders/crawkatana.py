from fileinput import filename
from pathlib import Path
from urllib import response
from bs4 import BeautifulSoup
import json

import scrapy


class QuotesSpider(scrapy.Spider):
    name = "auto"

    def __init__(self, katana_file=None, *args, **kwargs):
        super(QuotesSpider, self).__init__(*args, **kwargs)
        self.katana_file = katana_file

    def start_requests(self):
        if self.katana_file:
            # Carregar URLs do arquivo JSON do Katana
            with open(self.katana_file, 'r') as f:
                katana_data = json.load(f)
            
            # Assumindo que o Katana gera um formato como: {"urls": ["url1", "url2"]}
            # Ou uma lista de objetos com URLs
            for item in katana_data:
                if isinstance(item, dict) and 'url' in item:
                    yield scrapy.Request(url=item['url'], callback=self.parse)
                elif isinstance(item, str):
                    yield scrapy.Request(url=item, callback=self.parse)
        else:
            # URLs padrão se não houver arquivo Katana
            urls = [
                "https://me-liga.net",
                "https://www.nomesdefantasia.com",
            ]
            for url in urls:
                yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        page = response.url.split("/")[-2]
        filename = f"pages-{page}.html"
        Path(filename).write_bytes(response.body)
        self.log(f"Saved file {filename}")

        soup = BeautifulSoup(response.body, "html.parser")
        pretty_html = soup.prettify()
        Path(filename).write_text(pretty_html, encoding="utf-8")