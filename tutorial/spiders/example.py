from fileinput import filename
from pathlib import Path
from urllib import response
from bs4 import BeautifulSoup
import scrapy


class QuotesSpider(scrapy.Spider):
    name = "example"

# Add this before writing to file


    async def start(self):
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
