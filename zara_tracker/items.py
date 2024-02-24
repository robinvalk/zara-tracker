# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from peewee import *
import datetime
from zara_tracker.settings import DATABASE_FILEPATH

db = SqliteDatabase(DATABASE_FILEPATH)

class BaseModel(Model):
    class Meta:
        database = db

class Product(BaseModel):
    id = AutoField()
    zara_id = IntegerField()
    market = CharField()
    name = CharField()
    category = CharField()
    description = TextField()
    url = TextField()
    tracking = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.datetime.now)

class Color(BaseModel):
    id = AutoField()
    product = ForeignKeyField(Product, backref='colors')
    zara_id = IntegerField()
    name = CharField()
    image = TextField()

class ColorPriceTrace(BaseModel):
    color = ForeignKeyField(Color, backref='price_traces')
    price = IntegerField()
    old_price = IntegerField(null=True)
    original_price = IntegerField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)

class Size(BaseModel):
    id = AutoField()
    color = ForeignKeyField(Color, backref='sizes')
    zara_id = IntegerField()
    name = CharField()

class SizeAvailabilityTrace(BaseModel):
    size = ForeignKeyField(Size, backref='availability_traces')
    availability = CharField()
    created_at = DateTimeField(default=datetime.datetime.now)

class SizePriceTrace(BaseModel):
    size = ForeignKeyField(Size, backref='price_traces')
    price = IntegerField()
    old_price = IntegerField(null=True)
    original_price = IntegerField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)
