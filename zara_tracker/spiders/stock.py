from scrapy import Spider, Request
# from zara_tracker.items import ZaraTrackerItem, ZaraTrackerItemColor, ZaraTrackerItemColorSize

class ZaraSpider(Spider):
    name = "zara"
    allowed_domains = ["www.zara.com"]
    custom_settings = {
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "DOWNLOAD_HANDLERS": {
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
    }

    def start_requests(self):
        urls = [
            "https://www.zara.com/pl/pl/bluza-o-krotszym-kroju-z-kolekcji-basic-p08417803.html?v1=278099829",
            "https://www.zara.com/pl/pl/taliowana-sukienka-z-odkrytymi-plecami-p03641823.html?v1=290317149&v2=2354324",
            "https://www.zara.com/pl/pl/sukienka-sredniej-d%C5%82ugosci-z-wycieciami-p02298143.html?v1=267134062&v2=2354324&origin=shopcart",
            "https://www.zara.com/pl/pl/sukienka-w-stylu-bieliznianym-na-ramiaczkach-z-bizuteryjnymi-zdobieniami-p09196845.html?v1=316715661&v2=2354274",
            "https://www.zara.com/pl/pl/sukienka-sredniej-d%C5%82ugosci-na-ramiaczkach-z-plecionki-p07806670.html?v1=270399873&v2=2354274",
        ]

        for url in urls:
            yield Request(url, meta={
                "playwright": True,
                "playwright_include_page": True,
            })

    async def parse(self, response, **kwargs):
        page = response.meta["playwright_page"]
        payload = await page.evaluate("window.zara.viewPayload");
        await page.close()

        yield {
            "id": payload['product']['id'],
            "name": payload['product']['name'],
            "colors": self.map_colors(payload['product']['detail']['colors'])
        }

    def map_colors(self, colors):
        return [self.map_color(color) for color in colors]

    def map_color(self, color):
        return {
            "id": color['id'],
            "name": color['name'],
            "price": color['price'],
            "old_price": color.get('oldPrice', None),
            "original_price": color.get('originalPrice', None),
            "sizes": self.map_sizes(color['sizes'])
        }

    def map_sizes(self, sizes):
        return [self.map_size(size) for size in sizes]

    def map_size(self, size):
        return {
            "id": size['id'],
            "name": size['name'],
            "availability": size['availability'],
            "price": size['price'],
            "old_price": size.get('oldPrice', None),
            "original_price": size.get('originalPrice', None)
        }
