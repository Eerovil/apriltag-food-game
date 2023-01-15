from flask import Flask, render_template, request
from sqlitedict import SqliteDict
import os
import datetime
import random
import logging
from decimal import Decimal
import hashlib

from typing import List, Optional
from pydantic import BaseModel

data_folder = '../data'

app = Flask(__name__, static_url_path='/static', static_folder=data_folder, template_folder='')
logger = app.logger
logger.setLevel(logging.DEBUG)

main_table = SqliteDict(os.path.join(data_folder, 'main.db'), tablename="main", autocommit=True)

FRUIT_SLUGS = ['watermelon', 'carrot', 'apple', 'sandvich']

main_table['last_tick'] = datetime.datetime.now()


def table_setter(table, table_key, key, value):
    table_row = table[table_key]
    table_row[key] = value
    table[table_key] = table_row


INITIAL_CODES = [
    'http://koodi-1',
    'http://koodi-2',
    'http://koodi-3',
    'http://koodi-4',
    'http://koodi-5',
    'http://koodi-6',
    'http://koodi-7',
    'http://koodi-8',
    'http://koodi-9',
    'http://koodi-10',
    'http://koodi-11',
    'http://koodi-12',
]
HOME_CODE = 'http://koodi-6'


point_names = {
    'http://koodi-1': 'Eteisessä',
    'http://koodi-2': 'Sohvan takana',
    'http://koodi-3': 'Savupiipussa',
    'http://koodi-4': 'Kodinhoitohuoneessa',
    'http://koodi-5': 'Jääkaapissa',
    'http://koodi-6': 'Telkkarin Luona',
    'http://koodi-7': 'Kuivausrummussa',
    'http://koodi-8': 'Einarin Huoneessa',
    'http://koodi-9': 'Saunassa',
    'http://koodi-10': 'Makuuhuoneessa',
    'http://koodi-11': 'Valtterin huoneessa',
    'http://koodi-12': 'Vaatehuoneessa',
}



@app.route("/")
def hello_world():
    return render_template("client.html", title = 'App')
