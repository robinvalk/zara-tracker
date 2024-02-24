import scrapy
import logging
from zara_tracker.items import ColorPriceTrace, Color, Product
import datetime
from zara_tracker.telegram import send_telegram_message
from peewee import *
from zara_tracker.settings import COUNTRY_CODE, LANGUAGE_CODE, TG_TOKEN

class PricesSpider(scrapy.Spider):
    name = "prices"
    allowed_domains = ["www.zara.com"]
    start_urls = [f"https://www.zara.com/{COUNTRY_CODE}/{LANGUAGE_CODE}/categories?ajax=true"]
    sections_to_track = ["WOMAN", "MAN", "KID", "BEAUTY", "ZARA ORIGINS"]
    minimal_price_drop_percentage = 25

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(PricesSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.share_discount_reports, signal=scrapy.signals.engine_stopped)
        return spider

    def share_discount_reports(self):
        date = datetime.date.today()
        color_price_trace_sub_filter = ColorPriceTrace.alias('cpt') \
            .select(SQL('cpt.id')) \
            .where(
                (SQL('date(cpt.created_at)') == SQL(f"date('{date}')")) \
            )

        changed_product_ids_of_the_day = ColorPriceTrace.select(Product.id.distinct()) \
            .join(Color) \
            .join(Product) \
            .where(ColorPriceTrace.id << color_price_trace_sub_filter) \
            .group_by(Color.id) \
            .having(fn.Count(Color.id) > 1)

        changed_products = Product.select().where(Product.id.in_(changed_product_ids_of_the_day))

        for changed_product in changed_products:
            has_significant_price_drop = False

            for color in changed_product.colors:
                price_traces = color.price_traces.order_by(ColorPriceTrace.created_at.desc())

                if len(price_traces) <= 1:
                    logging.info(f"{changed_product.name} - {color.name} - Only 1 price tracked for this color, ignoring")
                    continue

                current_price = price_traces[0].price
                previous_price = price_traces[1].price

                # don't notify if price increased
                if current_price >= previous_price:
                    logging.info(f"{changed_product.name} - {color.name} - Price increased, ignoring. Previous price: {previous_price/100:.2f}, Current price: {current_price/100:.2f}")
                    continue

                # only notify if price drop is X% or higher
                discount_percentage = (previous_price - current_price) / previous_price * 100
                logging.info(f"{changed_product.name} - {color.name} - Current price: {current_price}, Previous price: {previous_price/100:.2f}, Discount percentage {discount_percentage}, Notifying {discount_percentage >= self.minimal_price_drop_percentage}")
                if discount_percentage >= self.minimal_price_drop_percentage:
                    has_significant_price_drop = True

            if has_significant_price_drop and TG_TOKEN:
                self.announce_product_price_change(changed_product)

    def announce_product_price_change(self, product):
        message = f"*{product.name}*\n\n"

        for color in product.colors:
            message += f"_{color.name}_\n"

            prices = []
            last_price = None
            for price_trace in color.price_traces.order_by(ColorPriceTrace.created_at):
                percentage = None if last_price is None else ((price_trace.price - last_price) / last_price * 100)
                percentage_text = f" ({round(percentage):+}%)" if percentage else ""
                prices.append(f"{price_trace.created_at:%Y-%m-%d}: {round(price_trace.price / 100, 2):.2f}{percentage_text}")
                last_price = price_trace.price

            prices.reverse()
            message += "\n".join(prices)

            message += f"\n\n"

        message += f"[Product page]({product.url})"

        send_telegram_message(product.market, color.image.split(", "), message)

    def parse(self, response):
        payload = response.json()

        sections = payload['categories']
        for section in sections:  # woman, man, kid, beauty, origins
            section_name = section.get('sectionName', section['name'])

            if section_name in self.sections_to_track:
                for category in self.process_category(section, []):
                    # print(f"Requesting category {category['id']}")
                    yield scrapy.Request(
                        f"https://www.zara.com/{COUNTRY_CODE}/{LANGUAGE_CODE}/category/{category['id']}/products?ajax=true",
                        callback = self.parse_products,
                        cb_kwargs = {
                            "market": section_name,
                            "category": category,
                        }
                    )

    def parse_products(self, response, market, category):
        payload = response.json()

        if not payload.get('productGroups'):
            logging.debug(f"{market}:{category['id']} - 'productGroups' is missing\n{payload.keys()}")
            return

        elements = payload['productGroups'][0]['elements']
        for element in elements:
            com_components = element.get('commercialComponents')

            if not com_components:
                logging.debug(f"{market}:{category['id']} - 'commercialComponents' is missing")
                continue

            for com_component in com_components:
                if not com_component.get('detail') \
                        or not com_component['detail'].get('colors') \
                        or not com_component.get('name') \
                        or not com_component.get('seo'):
                    logging.debug(f"{market}:{category['id']} - 'detail' or 'colors' or 'name' or 'seo' are missing\n{com_component.keys()}")
                    continue

                product_url = self.make_url(com_component['seo'], category['id'])
                if not product_url:
                    logging.debug(f"{market}:{category['id']} - 'product_url' is missing")
                    continue

                yield {
                    'id': com_component['seo']['seoProductId'],
                    'name': com_component['name'],
                    'market': market,
                    'url': product_url,
                    'category': category['name'],
                    'description': com_component.get('description', ''),
                    'colors': self.map_colors(com_component['detail']['colors'], market, category),
                }

    def map_colors(self, colors, market, category):
        items = []

        for color in colors:
            if not color.get('name') \
                    or not color.get('price') \
                    or not color.get('xmedia') \
                    or not color.get('productId'):
                logging.debug(f"{market}:{category['id']} - 'name' or 'price' or 'xmedia' or 'productId' are missing\n{color.keys()}")
                continue

            items.append(self.map_color(color))

        return items

    def map_color(self, color):
        return {
            "id": color['id'],
            "name": color['name'],
            "price": color['price'],
            "old_price": color.get('oldPrice', None),
            "original_price": color.get('originalPrice', None),
            "image": self.make_photo_urls(color['xmedia']),
            "sizes": self.map_sizes(color.get('sizes', []))
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

    def process_category(self, category, categories):
        for subcategory in category['subcategories']:
            if 'products' in subcategory['layout'] or 'marketing' in subcategory['layout']:
                self.process_category(subcategory, categories)
        else:
            category_id = category.get('redirectCategoryId', category['id'])
            category_name = self.formatting_category_name(category['name'])
            categories.append({'id': category_id, 'name': category_name})

        return categories

    def formatting_category_name(self, name: str):
        name = name.lower()
        if 'zara' in name:
            return name.replace('zara', '').strip()
        if '\xa0' in name:
            name = name.replace('\xa0', ' ')
        if ' | ' in name:
            return ' '.join(name.split(' | '))
        if ' ' in name:
            return name.replace(' ', '_')
        if '-' in name:
            return name.replace('-', '_')
        return name

    def make_url(self, seo: dict, category_id: str) -> str | None:
        if not seo.get('keyword'):
            return
        keyword = seo['keyword']
        seo_product_id = seo['seoProductId']
        discern_product_id = seo['discernProductId']
        url = f"https://www.zara.com/{COUNTRY_CODE}/{LANGUAGE_CODE}/{keyword}-p{seo_product_id}.html?v1={discern_product_id}&v2={category_id}"
        return url

    def make_photo_urls(self, photos: list) -> str:
        photos_list = []
        for photo in photos:
            path = photo['path']
            name = photo['name']
            timestamp = photo['timestamp']
            photo_str = f"https://static.zara.net/photos//{path}/w/750/{name}.jpg?ts={timestamp}"
            photos_list.append(photo_str)
        return ', '.join(photos_list)

    def get_percentage(self, price: int, price_old: int) -> str:
        percent = round(-1 * (100 - (price * 100 / price_old)))
        if percent > 0:
            percent = f'+{percent}'
        return str(percent)
