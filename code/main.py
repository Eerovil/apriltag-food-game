from collections import defaultdict
from flask import Flask, Response, render_template, request
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
tags_table = SqliteDict(os.path.join(data_folder, 'main.db'), tablename="tags", autocommit=True)

FRUIT_SLUGS = ['watermelon', 'carrot', 'apple', 'sandvich']

def fruit_name(fruit_slug):
    return {
        'watermelon': 'Vesimeloni',
        'carrot': 'Porkkana',
        'apple': 'Omena',
        'sandvich': 'Leipä',
    }.get(fruit_slug, fruit_slug)


def get_size_name():
    eaten_food = main_table.get('eaten_food', 0)
    if eaten_food < 1:
        return 'muurahainen'
    elif eaten_food < 2:
        return 'kärpänen'
    elif eaten_food < 5:
        return 'hiiri'
    elif eaten_food < 10:
        return 'kissa'
    elif eaten_food < 15:
        return 'lammas'
    elif eaten_food < 20:
        return 'leivinuuni'
    elif eaten_food < 25:
        return 'auto'
    elif eaten_food < 30:
        return 'talo'
    elif eaten_food < 35:
        return 'kirkko'
    elif eaten_food < 40:
        return 'kerrostalo'
    elif eaten_food < 45:
        return 'kaupunki'
    elif eaten_food < 50:
        return 'joki'
    elif eaten_food < 55:
        return 'kuu'
    elif eaten_food < 60:
        return 'maapallo'
    elif eaten_food < 65:
        return 'aurinko'
    elif eaten_food < 70:
        return 'galaksi'
    else:
        return 'universumi'

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


DAY_LENGTH = datetime.timedelta(seconds=60 * 2)
NIGHT_LENGTH = datetime.timedelta(seconds=30)


point_names = {
    'http://koodi-1': 'Eteisessä',
    'http://koodi-2': 'Sohvan takana',
    'http://koodi-3': 'Savupiipussa',
    'http://koodi-4': 'Kodinhoitohuoneessa',
    # 'http://koodi-5': 'Jääkaapissa',
    'http://koodi-6': 'Telkkarin Luona',
    'http://koodi-7': 'Kuivausrummussa',
    # 'http://koodi-8': 'Einarin Huoneessa',
    'http://koodi-9': 'Saunassa',
    'http://koodi-10': 'Makuuhuoneessa',
    'http://koodi-11': 'Valtterin huoneessa',
    'http://koodi-12': 'Vaatehuoneessa',
}



@app.route("/")
def hello_world():
    return render_template("client.html", title = 'App')


def dict_with_isoformat_dates(d):
    """
    Convert all datetime.datetime values to isoformat
    """
    d = d.copy()
    for key in d:
        if isinstance(d[key], datetime.datetime):
            d[key] = d[key].isoformat()
    return d


def set_day_status(new_status):
    main_table['day_status'] = new_status
    if new_status == 'day':
        main_table['day_status_ending'] = datetime.datetime.now() + DAY_LENGTH
    elif new_status == 'evening':
        main_table['day_status_ending'] = datetime.datetime.now() + datetime.timedelta(hours=1)
    elif new_status == 'night':
        main_table['day_status_ending'] = datetime.datetime.now() + NIGHT_LENGTH


def get_day_status():
    """
    Return day status and ending of the status,
    eg "day", "2022-01-01T12:00"
    """

    if not main_table.get('day_status'):
        main_table['day_status'] = 'day'
        main_table['day_status_ending'] = datetime.datetime.now() + DAY_LENGTH
        logger.debug('initializerd day status to day, ending at %s', main_table['day_status_ending'].isoformat())

    if main_table['day_status_ending'] < datetime.datetime.now():
        if main_table['day_status'] == 'day':
            set_day_status('evening')
            logger.debug('day ended, evening starting')
        elif main_table['day_status'] == 'evening':
            set_day_status('night')
            logger.debug('evening ended, night starting')
        elif main_table['day_status'] == 'night':
            set_day_status('day')
            logger.debug('night ended, day starting')
            respawn_all_tags()

    return main_table['day_status'], main_table['day_status_ending'].isoformat()


def respawn_all_tags():
    """
    E.g. when day starts. respawn all foods or other items.
    """
    fruit_tags = []
    for tag in point_names:
        tag_data = {}
        tag_data['last_seen'] = datetime.datetime.now() - datetime.timedelta(days=1)
        if tag != HOME_CODE:
            fruit_tags.append(tag)
        tags_table[tag] = tag_data

    # Randomize fruit tags
    random.shuffle(fruit_tags)

    # Make sure fruit_tags list is even
    if len(fruit_tags) % 2 == 1:
        fruit_tags.pop()

    # Spawn pairs of fruits
    for i in range(0, len(fruit_tags), 2):
        fruit_slug = random.choice(['watermelon', 'carrot', 'apple', 'sandvich'])
        table_setter(tags_table, fruit_tags[i], 'food', fruit_slug)
        table_setter(tags_table, fruit_tags[i + 1], 'food', fruit_slug)

    logger.debug('Respawned all tags')


def add_food_to_inventory(food_slug):
    """
    Add food to inventory
    """
    inventory = main_table['inventory']
    inventory.append({"slug": food_slug})
    main_table['inventory'] = inventory


def clear_tag(tag_slug):
    tag_data = tags_table[tag_slug]
    tag_data['food'] = None
    tags_table[tag_slug] = tag_data
    logger.debug('Cleared tag %s', tag_slug)


def all_food_collected():
    """
    Return True if all food has been collected
    """
    for tag in tags_table:
        if tags_table[tag].get('food'):
            return False
    return True


def check_tag_pairs():
    """
    If two tags are scanned recently and their food is a match, add that food to inventory
    """
    recent_tags = []
    recent_food_slugs = defaultdict(int)

    for tag in tags_table:
        if not tags_table[tag].get('food'):
            continue
        is_recent = datetime.datetime.now() - tags_table[tag]['last_seen'] < datetime.timedelta(seconds=10)
        if is_recent:
            food_slug = tags_table[tag]['food']
            recent_food_slugs[food_slug] += 1
            recent_tags.append(tag)

    event = None

    for tag in recent_tags:
        food_slug = tags_table[tag]['food']
        if recent_food_slugs[food_slug] < 2:
            continue

        # Add food to inventory
        add_food_to_inventory(food_slug)
        add_food_to_inventory(food_slug)
        logger.debug("Found food %s", food_slug)

        # Remove food from tag
        clear_tag(tag)

        # Remove other tag
        other_tag = [t for t in recent_tags if t != tag and tags_table[t]['food'] == food_slug][0]
        clear_tag(other_tag)

        event = {
            'type': 'food_found',
            'food_slug': food_slug,
            'point_name': point_names[tag],
        }
        break

    return event


@app.route("/api/scan", methods=['POST'])
def scan_tag():
    barcode = request.json.get('content')
    if not barcode:
        return 'No barcode provided'

    if 'koodi' not in barcode:
        return 'No koodi provided'

    if barcode not in tags_table:
        return Response('Unknown tag', status=404)

    day_status, day_status_ending = get_day_status()

    tag_data = tags_table[barcode]
    tag_data['last_seen'] = datetime.datetime.now()
    tags_table[barcode] = tag_data

    current_pos = None
    if barcode == HOME_CODE:
        current_pos = 'home'
    if tags_table[barcode].get('food'):
        current_pos = 'food'

    if day_status == 'day' and all_food_collected():
        set_day_status('evening')
        day_status, day_status_ending = get_day_status()

    speak = "Tyhjä"
    tag_pair_event = None
    if day_status == 'night':
        speak = "Nyt on yö, nukutaan"
    elif day_status == 'evening':
        speak = "Nyt on ilta, menkää nukkumaan"
        if current_pos == 'home':
            main_table['eaten_food'] += len(main_table['inventory'])
            speak = f"Syötte keräämänne ruoat, {len(main_table['inventory'])} kappaletta! Teistä kasvaa nyt yhtä isoja kuin {get_size_name()}."
            main_table['inventory'] = []
            set_day_status('night')
            day_status, day_status_ending = get_day_status()
    elif day_status == 'day':
        tag_pair_event = check_tag_pairs()

        if current_pos == 'home':
            speak = "tässä on koti, etsikää ruokaa!"
        elif tag_pair_event:
            speak = f"Saitte kerättyä ruuan {fruit_name(tag_pair_event['food_slug'])}!"
            if day_status == 'day' and all_food_collected():
                set_day_status('evening')
                day_status, day_status_ending = get_day_status()
        else:
            if current_pos == 'food':
                speak = f"tässä on ruoka {fruit_name(tag_data.get('food'))}, etsikää toinen!"

    return {
        'currentPos': current_pos,
        'posContent': dict_with_isoformat_dates(tags_table[barcode]),
        'collectedFruits': main_table['inventory'],
        'speak': speak,
        'dayStatus': day_status,
        'dayStatusEnding': day_status_ending,
        'event': tag_pair_event,
    }


### Initialize

respawn_all_tags()
main_table['inventory'] = []
main_table['eaten_food'] = 0
