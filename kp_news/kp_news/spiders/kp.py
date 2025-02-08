from typing import Iterable
import os

import scrapy
from scrapy import Request

from scrapy_playwright.page import PageMethod
from playwright._impl._page import Page

async def click_more_button(page: Page):
    await page.get_by_text('Показать еще').click()

async def page_load(page: Page):
    await page.wait_for_timeout(2000)


class KpSpider(scrapy.Spider):
    name = "kp"
    allowed_domains = ["kp.ru"]
    base_url = 'https://www.kp.ru'

    custom_settings = {
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': True,
        },
        'DOWNLOAD_HANDLERS': {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        'CLOSESPIDER_ITEMCOUNT': 1000,
        'ITEM_PIPELINES': {
            'kp_news.pipelines.PhotoDownloaderPipeline': 200,
            'kp_news.pipelines.MongoPipeline': 100,
        },
        'MONGO_DB': 'scrape_catalog',
        'MONGO_USER': os.getenv('MONGO_USER'),
        'MONGO_PASSWORD': os.getenv('MONGO_PASSWORD'),
        'MONGO_DC_COLLECTION': 'news'
    }
    default_articles_number = 25

    def start_requests(self) -> Iterable[Request]:
        yield Request(
            url='https://www.kp.ru/online/',
            meta={
                'playwright': True,
                'playwright_page_methods': [
                    PageMethod(click_more_button),
                    PageMethod(page_load)
                ] * (self.custom_settings['CLOSESPIDER_ITEMCOUNT'] // self.default_articles_number)
            }
        )

    def parse(self, response):
        hrefs = response.xpath("//a[@class = 'sc-1tputnk-2 drlShK']/@href").getall()
        for href in hrefs:
            yield Request(url=self.base_url + href, callback=self.parse_page)


    def parse_page(self, response):
        quote_author = response.xpath("//span[@class = 'sc-17oegr5-0 SUHig']/text()").get('')
        title = response.xpath("//h1/text()").get()
        description = response.xpath("//div[@class = 'sc-j7em19-4 nFVxV']/text()").get()
        publication_datetime = response.xpath("//span[@class = 'sc-j7em19-1 dtkLMY']/text()").get()
        article_text = '\n\n'.join(response.xpath("//p[@class = 'sc-1wayp1z-16 dqbiXu']/text()").getall())
        header_photo_url = response.xpath("//picture/img/@src").get()
        authors = response.xpath("//span[@class = 'sc-1jl27nw-1 bmkpOs']/text()").getall()
        keywords = response.xpath("//a[@class = 'sc-1vxg2pp-0 cXMtmu']/text()").getall()
        yield {
            'title': quote_author + title,
            'description': description,
            'article_text': article_text,
            'header_photo_url': header_photo_url,
            'publication_datetime': publication_datetime,
            'authors': authors,
            'keywords': keywords,
            'source_url': response.url,
        }


