# coding: utf-8
from argparse import ArgumentParser, Action
from asyncio import run
from asyncpg import connect
from collections import OrderedDict
from datetime import datetime, timedelta
from json import load, dump
from os import listdir, mkdir
from platform import system


players_query = '''
    SELECT count(account_id), console, _date
    FROM diff_battles
    WHERE _date >= '{}' AND _date < '{}'
    GROUP BY console, _date
    ORDER BY console, _date ASC
'''

battles_query = '''
    SELECT sum(battles), console, _date
    FROM diff_battles
    WHERE _date >= '{}' AND _date < '{}'
    GROUP BY console, _date
    ORDER BY console, _date ASC
'''

new_players_query = '''
    SELECT count(account_id), console, created_at::date
    FROM players
    WHERE created_at >= '{}' AND created_at < '{}'
    GROUP BY console, created_at::date
    ORDER BY console, created_at::date
'''

five_battles_a_day_query = '''
    SELECT count(*), console, _date
    FROM diff_battles
    WHERE battles >= 5 AND _date >= '{}' AND _date < '{}'
    GROUP BY console, _date
    ORDER BY _date, console
'''

async def query_active_accounts(conn, start, end=datetime.utcnow(), skip=False):
    dates = [(start + timedelta(days=i)).date() for i in range((end - start).days)]
    data = {
        'xbox': OrderedDict((d, 0) for d in dates),
        'ps': OrderedDict((d, 0) for d in dates)
    }
    players = await conn.fetch(players_query.format(start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')))

    for record in players:
        data[record['console']][record['_date']] = record['count']

    skip_next = False
    for key, value in data['ps'].items():
        if skip and value < 20000:
            skip_next = True
            continue
        elif skip and skip_next:
            skip_next = False
            continue

        with open('data/summary/active/' + key.strftime('%Y-%m-%d') + '.json', 'w') as f:
            dump({'xbox': data['xbox'][key], 'ps': data['ps'][key]}, f)


async def query_battles(conn, start, end=datetime.utcnow(), skip=False):
    dates = [(start + timedelta(days=i)).date() for i in range((end - start).days)]
    data = {
        'xbox': OrderedDict((d, 0) for d in dates),
        'ps': OrderedDict((d, 0) for d in dates)
    }
    battles = await conn.fetch(battles_query.format(start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')))

    for record in battles:
        data[record['console']][record['_date']] = record['sum']

    skip_next = False
    for key, value in data['ps'].items():
        if skip and value < 400000:
            skip_next = True
            continue
        elif skip and skip_next:
            skip_next = False
            continue

        with open('data/summary/battles/' + key.strftime('%Y-%m-%d') + '.json', 'w') as f:
            dump({'xbox': data['xbox'][key], 'ps': data['ps'][key]}, f)


async def query_new_players(conn, start, end=datetime.utcnow()):
    dates = [(start + timedelta(days=i)).date() for i in range((end - start).days)]
    data = {
        'xbox': OrderedDict((d, 0) for d in dates),
        'ps': OrderedDict((d, 0) for d in dates)
    }
    new_players = await conn.fetch(new_players_query.format(start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')))

    for record in new_players:
        data[record['console']][record['created_at']] = record['count']

    for key in data['ps']:
        with open('data/summary/new/' + key.strftime('%Y-%m-%d') + '.json', 'w') as f:
            dump({'xbox': data['xbox'][key], 'ps': data['ps'][key]}, f)


async def query_min_5_a_day(conn, start, end=datetime.utcnow(), skip=False):
    dates = [(start + timedelta(days=i)).date() for i in range((end - start).days)]
    data = {
        'xbox': OrderedDict((d, 0) for d in dates),
        'ps': OrderedDict((d, 0) for d in dates)
    }
    five_battles = await conn.fetch(five_battles_a_day_query.format(start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')))

    for record in five_battles:
        data[record['console']][record['_date']] = record['count']

    skip_next = False
    for key, value in data['ps'].items():
        if skip and value < 20000:
            skip_next = True
            continue
        elif skip and skip_next:
            skip_next = False
            continue

        with open('data/summary/min5/' + key.strftime('%Y-%m-%d') + '.json', 'w') as f:
            dump({'xbox': data['xbox'][key], 'ps': data['ps'][key]}, f)


def create_file_listings():
    active = listdir('data/summary/active/')
    with open('data/available/active.txt', 'w') as f:
        f.writelines(map(lambda l: l.split('.')[0] + '\n', sorted(active)))
    battles = listdir('data/summary/battles/')
    with open('data/available/battles.txt', 'w') as f:
        f.writelines(map(lambda l: l.split('.')[0] + '\n', sorted(battles)))
    min5 = listdir('data/summary/min5/')
    with open('data/available/min5.txt', 'w') as f:
        f.writelines(map(lambda l: l.split('.')[0] + '\n', sorted(min5)))


def setup_directories():
    dirs = (  # Order-dependent!
        'data', 'data/available', 'data/summary', 'data/summary/active',
        'data/summary/battles', 'data/summary/new', 'data/summary/min5'
    )
    for d in dirs:
        try:
            mkdir(d)
        except FileExistsError:
            pass


async def export_data(config, args):
    setup_directories()
    db = await connect(**config['database'])
    await query_active_accounts(db, args.start, args.end, args.skip)
    await query_battles(db, args.start, args.end, args.skip)
    await query_new_players(db, args.start, args.end)
    await query_min_5_a_day(db, args.start, args.end, args.skip)
    create_file_listings()


class ConvertTime(Action):
    def __call__(self, parser, namespace, values, default, option_string=None, skip_dates=None):
        if values is None:
            setattr(namespace, self.dest, default)
        elif isinstance(values, datetime):
            setattr(namespace, self.dest, values)
        elif isinstance(values, str):
            setattr(namespace, self.dest, datetime.strptime(values, '%Y-%m-%d'))
        else:
            raise Exception('Invalid format')


if __name__ == '__main__':
    agp = ArgumentParser()
    agp.add_argument('-s', '--start', default=datetime(2014, 1, 1, 0, 0), action=ConvertTime, help='%%Y-%%m-%%d format')
    agp.add_argument('-c', '--config', default='config.json')
    agp.add_argument('-e', '--end', default=datetime.utcnow(), action=ConvertTime, help='%%Y-%%m-%%d format')
    agp.add_argument('--skip', action='store_true')

    args = agp.parse_args()

    with open(args.config) as f:
        config = load(f)

    if system() == 'Windows':
        from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy
        set_event_loop_policy(WindowsSelectorEventLoopPolicy())
    run(export_data(config, args))
