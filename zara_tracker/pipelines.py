# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter, is_item
from zara_tracker.items import Product, Color, ColorPriceTrace, Size, SizeAvailabilityTrace, SizePriceTrace, db
from scrapy.exceptions import DropItem

import logging
from peewee import *

class ZaraTrackerPipeline:
    def __init__(self):
        db.connect()
        db.create_tables([Product, Color, ColorPriceTrace, Size, SizeAvailabilityTrace, SizePriceTrace])

    def process_item(self, item, spider):
        product, created_product = Product.get_or_create(
            zara_id = item.get('id'),
            defaults = {
                'name': item.get('name'),
                'market': item.get('market'),
                'category': item.get('category'),
                'description': item.get('description'),
                'url': item.get('url'),
            }
        )
        logging.debug(f"{product.name}")

        colors = item.get('colors', [])
        if colors:
            self.store_colors(product, colors)

    def store_colors(self, product, colors):
        for c in colors:
            color, created_color = Color.get_or_create(
                zara_id = c.get('id'),
                product = product,
                defaults = {
                    'name': c.get('name'),
                    'image': c.get('image'),
                }
            )

            color_price_trace = ColorPriceTrace.select().where(ColorPriceTrace.color == color).order_by(ColorPriceTrace.created_at.desc()).first()

            if created_color or (color_price_trace and color_price_trace.price != c.get('price')):
                color_price_trace = ColorPriceTrace.create(
                    color = color,
                    price = c.get('price'),
                    old_price = c.get('old_price'),
                    original_price = c.get('original_price'),
                )

            logging.debug(f"{color.product.name} - {color.name}")
            # sizes = c.get('sizes', [])
            # if sizes:
            #     self.store_sizes(color, sizes)

    def store_sizes(self, color: Color, sizes):
        for s in sizes:
            size, created_size = Size.get_or_create(
                zara_id = s.get('id'),
                color = color,
                defaults = {
                    'name': s.get('name'),
                }
            )
            logging.debug(f"{size.color.product.name} - {size.color.name} - {size.name}")

            size_price_trace = SizeAvailabilityTrace.get(
                (SizeAvailabilityTrace.size == size) &
                (SizeAvailabilityTrace.availability == s.get('availability'))
            ).order_by(SizeAvailabilityTrace.created_at.desc())

            if not size_availability_trace or created_size:
                size_availability_trace = SizeAvailabilityTrace.create(
                    size = size,
                    availability = s.get('availability'),
                )
                logging.debug(f"{size.color.product.name} - {size.color.name} - {size.name} - Availability")

            size_price_trace = SizePriceTrace.get(
                (SizePriceTrace.size == size) &
                (SizePriceTrace.price == s.get('price'))
            ).order_by(SizePriceTrace.created_at.desc())

            if not size_price_trace or created_size:
                size_price_trace = SizePriceTrace.create(
                    size = size,
                    price = s.get('price'),
                    old_price = s.get('old_price'),
                    original_price = s.get('original_price'),
                )
                logging.debug(f"{size.color.product.name} - {size.color.name} - {size.name} - Price")
