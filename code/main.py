from collections import defaultdict
from flask import Flask, Response, render_template, request
from sqlitedict import SqliteDict
import os
import datetime
import random
import logging
from decimal import Decimal
import hashlib
import glob

from typing import List, Optional
from pydantic import BaseModel

data_folder = '../data'

app = Flask(__name__, static_url_path='/static', static_folder=data_folder, template_folder='')
logger = app.logger
logger.setLevel(logging.DEBUG)

main_table = SqliteDict(os.path.join(data_folder, 'main.db'), tablename="main", autocommit=True)
tags_table = SqliteDict(os.path.join(data_folder, 'main.db'), tablename="tags", autocommit=True)

player_tables = []

FRUIT_SLUGS = ['watermelon', 'carrot', 'apple', 'sandvich', 'ananas', 'banana', 'strawberry']


def initialize_table_key(table, key, value):
    if key not in table:
        table[key] = value


def get_player_table(request):
    ip_address = request.remote_addr
    player_table = SqliteDict(os.path.join(data_folder, ip_address.replace('.', '_') + '.db'), tablename="main", autocommit=True)
    for elf in ELFS.keys():
        initialize_table_key(player_table, f'{elf}_elf_counter', 0)
        initialize_table_key(player_table, f'{elf}_elf_used', False)

    initialize_table_key(player_table, 'last_tag', None)

    initialize_table_key(player_table, 'sun_dance_progress', 0)

    player_tables.append(player_table)

    return player_table


def fruit_name(fruit_slug):
    return {
        'watermelon': 'Vesimeloni',
        'carrot': 'Porkkana',
        'apple': 'Omena',
        'sandvich': 'Leipä',
        'ananas': 'Ananas',
        'banana': 'Banaani',
        'strawberry': 'Mansikka',
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


DAY_LENGTH = datetime.timedelta(seconds=60 * 3)
NIGHT_LENGTH = datetime.timedelta(seconds=30)


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


ELFS = {
    'saunatonttu': 'http://koodi-9',
    'vaatehuonetonttu': 'http://koodi-12',
    'eteistonttu': 'http://koodi-1',
    'telkkaritonttu': 'http://koodi-6',
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
    logger.debug('set day status to %s, ending at %s', new_status, main_table['day_status_ending'].isoformat())


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
            main_table['eaten_food_today'] = 0
        elif main_table['day_status'] == 'evening':
            set_day_status('night')
            logger.debug('evening ended, night starting')
        elif main_table['day_status'] == 'night':
            set_day_status('day')
            logger.debug('night ended, day starting')
            respawn_all_tags()

    return main_table['day_status'], main_table['day_status_ending'].isoformat()


def respawn_all_tags(init=False):
    """
    E.g. when day starts. respawn all foods or other items.
    Don't respawn tags that have food on them.
    """
    for player_table in player_tables:
        for elf in ELFS.keys():
            player_table[f'{elf}_elf_counter'] = 0
            player_table[f'{elf}_elf_used'] = False
            main_table[f'{elf}_elf_used'] = False

        player_table['sun_dance_progress'] = 0
        player_table['last_tag'] = None

    if not main_table['sun_dance_steps']:
        # Add 3 random points as sun dance steps
        sun_dance_steps = []
        for i in range(3):
            sun_dance_steps.append(random.choice(list(point_names.keys())))
        main_table['sun_dance_steps'] = sun_dance_steps
    logger.debug("Sun dance steps: %s", main_table['sun_dance_steps'])

    empty_tags = []
    for tag in point_names:
        if tags_table.get(tag) and tags_table[tag].get('food'):
            # Already has food, don't respawn
            if not init:
                continue
        tag_data = {}
        tag_data['last_seen'] = datetime.datetime.now() - datetime.timedelta(days=1)
        empty_tags.append(tag)
        tags_table[tag] = tag_data

    # Randomize fruit tags
    random.shuffle(empty_tags)

    # Respawn hint
    if len(empty_tags) > 0:
        table_setter(tags_table, empty_tags[0], 'hint', True)
        logger.debug("Hint respawned in tag %s", empty_tags[0])
        empty_tags.pop(0)

    if random.randint(0, 1) == 0:
        # 50% chance to respawn sun dance hint
        if len(empty_tags) > 0:
            table_setter(tags_table, empty_tags[0], 'sun_dance_hint', True)
            logger.debug("Sun dance hint respawned in tag %s", empty_tags[0])
            empty_tags.pop(0)

    # Make sure empty_tags list is even
    if len(empty_tags) % 2 == 1:
        empty_tags.pop()

    available_fruits = list(FRUIT_SLUGS)
    # Remove fruits that are already spawned
    for tag in tags_table:
        if tags_table[tag].get('food') in available_fruits:
            available_fruits.remove(tags_table[tag].get('food'))

    if len(available_fruits) == 0:
        # Add one more fruit
        available_fruits.append(random.choice(FRUIT_SLUGS))

    # Spawn pairs of fruits
    counter = 0
    for i in range(0, len(empty_tags), 2):
        fruit_slug = available_fruits[counter % len(available_fruits)]
        table_setter(tags_table, empty_tags[i], 'food', fruit_slug)
        table_setter(tags_table, empty_tags[i + 1], 'food', fruit_slug)
        counter += 1

    logger.debug('Respawned all tags: init: %s', init)
    main_table['last_tag'] = None


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


def check_tag_pair(request, new_tag):
    """
    If prev tag food is a match, add that food to inventory
    """
    player_table = get_player_table(request)
    event = None
    if player_table['last_tag'] and player_table['last_tag'] != new_tag:
        prev_tag_data = tags_table[player_table['last_tag']]
        new_tag_data = tags_table[new_tag]
        prev_food = prev_tag_data.get('food')
        new_food = new_tag_data.get('food')

        if prev_food and new_food and prev_food == new_food:
            add_food_to_inventory(prev_food)
            add_food_to_inventory(prev_food)
            clear_tag(player_table['last_tag'])
            clear_tag(new_tag)

            event = {
                'type': 'food_found',
                'food_slug': prev_food,
                'point_name': point_names[new_tag],
            }

    player_table['last_tag'] = new_tag

    return event


def get_hint_text():
    """
    Return a hint that contains a pair as text
    """
    tags = []
    for tag in tags_table:
        if tags_table[tag].get('food'):
            tags.append(tag)

    random_tag = random.choice(tags)
    random_food = tags_table[random_tag]['food']

    for tag in tags_table:
        if tags_table[tag].get('food') == random_food and tag != random_tag:
            return 'Vihje: %s ja %s' % (point_names[random_tag], point_names[tag])

    return 'Ei mitään'


def get_hint2_text():
    """
    Return a hint that contains three random food locations
    """
    tags = []
    for tag in tags_table:
        if tags_table[tag].get('food'):
            tags.append(tag)

    tags = random.sample(tags, 3)
    ret = ""
    for tag in tags:
        ret += point_names[tag] + " on " + fruit_name(tags_table[tag]['food']) + ". "

    return ret or 'Ei mitään'


def get_sun_dance_hint_text():
    """
    Return a hint that contains the dance steps as text
    """
    return (
        "Avaat vanhan näköisen pergamentin. Paperi on kellastunut ja kirjoitus on hauras. " +
        "Olet löytänyt vanhan auringonpäivän tanssin ohjeen. Piippaa järjestyksessä: " +
        (", ".join([point_names[_tag] for _tag in main_table['sun_dance_steps']]))
    )


def get_joke_text():
    """
    Return a random joke
    """
    JOKES = [
        "Miksi joulupukki ei anna apulaistensa valjastaa poroa? Koska ne ovat aivan tonttuja.",
        "Mikä on suurempi kuin joulukuusi? Jouluseitsemän.",
        "Mihin joulu päättyy? U-kirjaimeen. ",
        "Mitä tapahtui tontulle joka hukkasi lakkinsa? Siltä jäätyi korva tunturilla.",
    ]
    return random.choice(JOKES)


def get_elf_speak(elf_data):
    rand = random.randint(1, 5)
    if main_table[f'{elf_data}_elf_used']:
        return f'{elf_data} on lähtenyt. Yritä huomenna uudelleen.'
    main_table[f'{elf_data}_elf_used'] = True

    ret = f'Herätit {elf_data}. '.replace('tonttu', 'tontun')

    result = 'nothing'
    if elf_data == 'saunatonttu':
        if rand == 1:
            result = 'lose_food'
        if rand >= 3:
            result = 'hint'
    elif elf_data == 'vaatehuonetonttu':
        if rand <= 2:
            result = 'lose_food'
        if rand >= 3:
            result = 'hint2'
    elif elf_data == 'eteistonttu':
        if rand == 1:
            result = 'lose_food'
        if rand >= 4:
            result = 'sun_dance_hint'
    elif elf_data == 'telkkaritonttu':
        result = 'joke'

    if result == 'lose_food':
        # 20% change to lose food
        main_table['inventory'] = []
        return ret + f'{elf_data} on vihainen ja syö kaiken ruuan. Yritä huomenna uudelleen.'
    if result == 'hint':
        return ret + f'{elf_data} antaa sinulle vihjeen. ' + get_hint_text()
    if result == 'hint2':
        return ret + f'{elf_data} paljastaa olinpaikkoja. ' + get_hint2_text()
    if result == 'sun_dance_hint':
        return (
            ret + f'{elf_data} kertoo sinulle aurinkotanssin ohjeen. ' + "Piippaa järjestyksessä: " +
            (", ".join([point_names[_tag] for _tag in main_table['sun_dance_steps']]))
        )
    if result == 'joke':
        return f'{elf_data} kertoo vitsin: ' + get_joke_text() + " Heh heh! Olipas hauskaa!"

    # 20% change to nothing happen
    return ret + f'{elf_data} on tänään väsynyt ja ei sano mitään. Yritä huomenna uudelleen.'


def get_success_sun_dance_speak(request):
    """
    Apply sun dance success and speak
    """
    player_table = get_player_table(request)
    main_table['sun_dance_steps'] = []
    player_table['sun_dance_progress'] = 0

    main_table['day_status_ending'] += datetime.timedelta(minutes=2)
    return 'Tunnet kuinka aurinko liikkuu väärään suuntaan. Päivä on pidentynyt kahdella minuutilla! Olet tanssinut aurinkotanssin!'


@app.route("/api/scan", methods=['POST'])
def scan_tag():
    barcode = request.json.get('content')
    if not barcode:
        return 'No barcode provided'

    player_table = get_player_table(request)

    if barcode != 'dummy':
        if 'koodi' not in barcode:
            return 'No koodi provided'

        if barcode not in tags_table:
            return Response('Unknown tag', status=404)

        tag_data = tags_table[barcode]
        tag_data['last_seen'] = datetime.datetime.now()
        tags_table[barcode] = tag_data

    else:
        tag_data = None

    day_status, day_status_ending = get_day_status()

    current_pos = None
    if barcode == 'dummy':
        current_pos = 'dummy'
    elif tags_table[barcode].get('food'):
        current_pos = 'food'
    elif tags_table[barcode].get('hint'):
        current_pos = 'hint'
        table_setter(tags_table, barcode, 'hint', False)
    elif tags_table[barcode].get('sun_dance_hint'):
        current_pos = 'sun_dance_hint'
        table_setter(tags_table, barcode, 'sun_dance_hint', False)

    if day_status == 'day' and all_food_collected():
        set_day_status('evening')
        main_table['eaten_food_today'] = 0
        day_status, day_status_ending = get_day_status()

    eat_all_food_event = None
    if not main_table['inventory'] and main_table['day_status'] == 'evening':
        set_day_status('night')
        day_status, day_status_ending = get_day_status()
        eat_all_food_event = {
            'type': 'eat_all_food',
            'speak': ''
        }
        if main_table['eaten_food_today'] == 0:
            eat_all_food_event['speak'] = f"Ette saaneet kerättyä yhtään ruokaa. Olette yhtä isoja kuin {get_size_name()}."
        else:
            eat_all_food_event['speak'] = f"Söitte keräämänne ruoat, {main_table['eaten_food_today']} kappaletta! Teistä kasvaa nyt yhtä isoja kuin {get_size_name()}."

        eat_all_food_event['speak'] += " Nyt nukkumaan!"

    speak = "etsikää ruokapareja!"
    tag_pair_event = None
    if day_status == 'night':
        speak = "Nyt on yö, nukutaan"
    elif day_status == 'evening':
        speak = "Nyt on ilta, on aika syödä iltapala"
    elif day_status == 'day':
        if tag_data:
            tag_pair_event = check_tag_pair(request, barcode)

        if tag_pair_event:
            speak = f"Löytyi pari! {fruit_name(tag_pair_event['food_slug'])}!"
            if day_status == 'day' and all_food_collected():
                set_day_status('evening')
                day_status, day_status_ending = get_day_status()
        else:
            if current_pos == 'food':
                speak = f"tässä on {fruit_name(tag_data.get('food'))}, Missä on sen pari?"
            elif current_pos == 'hint':
                speak = get_hint_text()
            elif current_pos == 'sun_dance_hint':
                speak = get_sun_dance_hint_text()
            elif not current_pos:
                speak = "Tyhjä"

        for elf_data, elf_tag in ELFS.items():
            if barcode == elf_tag:
                player_table[f'{elf_data}_elf_counter'] += 1
                logger.debug(f"{elf_data} elf counter: {player_table[f'{elf_data}_elf_counter']}")
                if player_table[f'{elf_data}_elf_counter'] == 2:
                    speak = get_elf_speak(elf_data)
                elif player_table[f'{elf_data}_elf_counter'] == 1:
                    speak += ". Jotain vilahti, olikohan se tonttu? "
            else:
                player_table[f'{elf_data}_elf_counter'] = 0

    if main_table['sun_dance_steps']:
        if barcode == main_table['sun_dance_steps'][player_table['sun_dance_progress']]:
            player_table['sun_dance_progress'] += 1
            logger.debug(f"Sun dance progress: {player_table['sun_dance_progress']}")
            if player_table['sun_dance_progress'] == len(main_table['sun_dance_steps']):
                speak = get_success_sun_dance_speak(request)
        else:
            player_table['sun_dance_progress'] = 0

    return {
        'currentPos': current_pos,
        'posContent': dict_with_isoformat_dates(tags_table[barcode]) if tag_data else None,
        'collectedFruits': main_table['inventory'],
        'speak': speak,
        'dayStatus': day_status,
        'dayStatusEnding': day_status_ending,
        'event': tag_pair_event or eat_all_food_event,
    }


@app.route("/api/eat_food", methods=['POST'])
def eat_food():
    eat_slug = request.json.get('eatSlug')
    if eat_slug:
        inventory = main_table['inventory']
        index = 0
        for food in inventory:
            if food['slug'] == eat_slug:
                inventory.pop(index)
                main_table['inventory'] = inventory
                main_table['eaten_food_today'] += 1
                main_table['eaten_food'] += 1
                break
            index += 1

    return {
        'collectedFruits': main_table['inventory'],
    }



### Initialize

# Delete all *.db files in data_folder
for file in os.listdir(data_folder):
    if file.endswith(".db"):
        if file == 'main.db':
            continue
        os.remove(os.path.join(data_folder, file))

respawn_all_tags(init=True)
main_table['inventory'] = []
main_table['eaten_food'] = 0
main_table['eaten_food_today'] = 0

set_day_status('day')

for tag in tags_table:
    print(f"Tag: {tag}, food: {tags_table[tag].get('food')}")
