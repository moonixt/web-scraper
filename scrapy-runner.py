#!/usr/bin/env python3
"""Utility script to run the Scrapy pipeline using Katana JSONL output."""

import argparse
import json
import logging
import os
import re
from datetime import datetime
from typing import List

try:
    import scrapy  # type: ignore
    from scrapy import signals  # type: ignore
    from scrapy.crawler import CrawlerProcess  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError(
        "Scrapy is required to run this script. Install dependencies with `pip install -r requirements.txt`."
    ) from exc


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_urls_from_jsonl(path: str, limit: int | None = None) -> List[str]:
    """Read Katana JSONL file and return list of URLs."""
    if not os.path.exists(path):
        logger.warning("Katana JSONL file not found: %s", path)
        return []

    urls: List[str] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            url = payload.get("url")
            if url:
                urls.append(url)
                if limit and len(urls) >= limit:
                    break
    return urls


class PageSpider(scrapy.Spider):
    name = "page"
    custom_settings = {
        "DOWNLOAD_DELAY": 0.5,
        "USER_AGENT": "ICMS SEO Analyzer/1.0 (+https://fluxo.software)",
        "LOG_LEVEL": "WARNING",
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 2.0,
        "CONCURRENT_REQUESTS": 8,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 1,
        "REDIRECT_ENABLED": True,
    }

    def __init__(self, katana_file: str, output: str, category: str | None = None, limit: int | None = 30, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.katana_file = katana_file
        self.category = category or "generic"
        self.output = output
        self.limit = limit
        self.pages: List[dict] = []
        self.start_urls = load_urls_from_jsonl(katana_file, limit=self.limit)
        if not self.start_urls:
            logger.warning("No URLs provided to spider. Katana JSONL might be empty.")

    def parse(self, response: scrapy.http.Response, **kwargs):  # type: ignore[override]
        body_text = " ".join(
            text.strip()
            for text in response.xpath("//body//text()").getall()
            if text and text.strip()
        )
        word_count = len(re.findall(r"\w+", body_text))

        page_data = {
            "url": response.url,
            "status": response.status,
            "title": response.css("title::text").get(default="").strip(),
            "meta_description": response.css("meta[name='description']::attr(content)").get(default="").strip(),
            "h1_count": len(response.css("h1").getall()),
            "word_count": word_count,
            "h1_samples": [h1.strip() for h1 in response.css("h1::text").getall() if h1.strip()],
            "headers": {
                "h2": [h2.strip() for h2 in response.css("h2::text").getall() if h2.strip()],
                "h3": [h3.strip() for h3 in response.css("h3::text").getall() if h3.strip()],
            },
        }
        self.pages.append(page_data)
        yield page_data

    def close(self, reason):  # type: ignore[override]
        logger.info("Spider finished: %s (%s pages)", reason, len(self.pages))
        os.makedirs(os.path.dirname(self.output) or ".", exist_ok=True)
        payload = {
            "category": self.category,
            "generated_at": datetime.now().isoformat(),
            "pages": self.pages,
        }
        with open(self.output, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)


def run_spider(katana_file: str, output: str, category: str | None, limit: int | None):
    process = CrawlerProcess()
    finished = {"status": False}

    def mark_finished(*_args, **_kwargs):
        finished["status"] = True

    process.signals.connect(mark_finished, signal=signals.spider_closed)
    process.crawl(PageSpider, katana_file=katana_file, output=output, category=category, limit=limit)
    process.start()

    if not finished["status"]:
        raise RuntimeError("Spider did not complete properly")


def main():
    parser = argparse.ArgumentParser(description="Run Scrapy spider over Katana JSONL data")
    parser.add_argument("--input", dest="katana_file", required=True, help="Path to Katana JSONL file")
    parser.add_argument("--output", dest="output", required=True, help="Path to write SEO JSON output")
    parser.add_argument("--category", dest="category", default="generic", help="Category name for metadata")
    parser.add_argument("--limit", dest="limit", type=int, default=30, help="Maximum number of URLs to crawl")

    args = parser.parse_args()
    urls = load_urls_from_jsonl(args.katana_file, limit=args.limit)
    if not urls:
        logger.warning("No URLs found in Katana file, creating empty output")
        payload = {"category": args.category, "generated_at": datetime.now().isoformat(), "pages": []}
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        return

    run_spider(args.katana_file, args.output, args.category, args.limit)


if __name__ == "__main__":
    main()
