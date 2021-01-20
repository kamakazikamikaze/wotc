# coding: utf-8
from argparse import ArgumentParser, Action
from datetime import datetime, timedelta
from elasticsearch6 import Elasticsearch
from json import load, dump

players_query = {
    "aggs": {
        "2": {
            "date_histogram": {
                "field": "date",
                "interval": "1d",
                "min_doc_count": 0
            },
            "aggs": {
                "3": {
                    "terms": {
                        "field": "console.keyword",
                        "size": 2,
                        "order": {
                            "_count": "desc"
                        },
                        "min_doc_count": 0
                    }
                }
            }
        }
    },
    "size": 0,
    "_source": {"excludes": []},
    "stored_fields": ["*"],
    "script_fields": {},
    "docvalue_fields": [
        {
            "field": "date",
            "format": "date_time"
        }
    ],
    "query": {
        "bool": {
            "must": [
                {"match_all": {}},
                {"match_all": {}},
                {
                    "range": {
                        "date": {
                            "gte": None,
                            "lte": None,
                            "format": "date"
                        }
                    }
                }
            ],
            "filter": [],
            "should": [],
            "must_not": []
        }
    }
}

battles_query = {
    "aggs": {
        "2": {
            "date_histogram": {
                "field": "date",
                "interval": "1d",
                "min_doc_count": 0
            },
            "aggs": {
                "3": {
                    "terms": {
                        "field": "console.keyword",
                        "size": 2,
                        "order": {
                            "1": "desc"
                        },
                        "min_doc_count": 0
                    },
                    "aggs": {
                        "1": {
                            "sum": {
                                "field": "battles"
                            }
                        }
                    }
                }
            }
        }
    },
    "size": 0,
    "_source": {"excludes": []},
    "stored_fields": ["*"],
    "script_fields": {},
    "docvalue_fields": [
        {
            "field": "date",
            "format": "date_time"
        }
    ],
    "query": {
        "bool": {
            "must": [
                {"match_all": {}},
                {"match_all": {}},
                {
                    "range": {
                        "date": {
                            "gte": None,
                            "lte": None,
                            "format": "date"
                        }
                    }
                }
            ],
            "filter": [],
            "should": [],
            "must_not": []
        }
    }
}

new_players_query = {
    "aggs": {
        "2": {
            "date_histogram": {
                "field": "created_at",
                "interval": "1d",
                "min_doc_count": 0
            },
            "aggs": {
                "3": {
                    "terms": {
                        "field": "console.keyword",
                        "size": 2,
                        "order": {
                            "_count": "desc"
                        },
                        "min_doc_count": 0
                    }
                }
            }
        }
    },
    "size": 0,
    "_source": {"excludes": []},
    "stored_fields": ["*"],
    "script_fields": {},
    "docvalue_fields": [
        {
            "field": "created_at",
            "format": "date_time"
        }
    ],
    "query": {
        "bool": {
            "must": [
                {"match_all": {}},
                {"match_all": {}},
                {
                    "range": {
                        "created_at": {
                            "gte": None,
                            "lt": None,
                            "format": "date"
                        }
                    }
                }
            ],
            "filter": [],
            "should": [],
            "must_not": []
        }
    }
}

five_battles_a_day_query = {
    'aggs': {
        '4': {
            'date_histogram': {
                'field': 'date',
                'interval': '1d',
                'min_doc_count': 0
            },
            'aggs': {
                '3': {
                    'terms': {
                        'field': 'console.keyword',
                        'size': 2,
                        'order': {'_count': 'desc'}
                    },
                    'aggs': {
                        '2': {
                            'range': {
                                'field': 'battles',
                                'ranges': [{'from': 5, 'to': None}],
                                'keyed': True
                            }
                        }
                    }
                }
            }
        }
    },
    'size': 0,
    '_source': {'excludes': []},
    'stored_fields': ['*'],
    'script_fields': {},
    'docvalue_fields': [{'field': 'date', 'format': 'date_time'}],
    'query': {
        'bool': {
            'must': [
                {'match_all': {}},
                {'match_all': {}},
                {
                    'range': {
                        'date': {
                            'gte': None,
                            'lte': None,
                            'format': 'date'
                        }
                    }
                }
            ],
            'filter': [],
            'should': [],
            'must_not': []
        }
    }
}

def timerange(start, end=datetime.utcnow(), step=90):
    delta = timedelta(days=step)
    next_iter = start
    while end > next_iter:
        yield (next_iter, next_iter + delta)
        next_iter = next_iter + delta


def query_active_accounts(elastic, index, start, end=datetime.utcnow(), step=90):
    tr = timerange(start, end, step)
    for older, newer in tr:
        players_query['query']['bool'][
                'must'][-1]['range']['date']['gte'] = older.strftime('%Y-%m-%d')
        players_query['query']['bool'][
                'must'][-1]['range']['date']['lte'] = newer.strftime('%Y-%m-%d')
        players = elastic.search(index=index, body=players_query)

        for bucket in players['aggregations']['2']['buckets']:
            key = bucket['key_as_string'].split('T')[0]
            if not bucket['3']['buckets']:
                continue
            data = {}
            for subbucket in bucket['3']['buckets']:
                data[subbucket['key']] = subbucket['doc_count']
            with open('data/summary/active/' + key + '.json', 'w') as f:
                dump(data, f)


def query_battles(elastic, index, start, end=datetime.utcnow(), step=90):
    tr = timerange(start, end, step)
    for older, newer in tr:
        battles_query['query']['bool'][
                'must'][-1]['range']['date']['gte'] = older.strftime('%Y-%m-%d')
        battles_query['query']['bool'][
                'must'][-1]['range']['date']['lte'] = newer.strftime('%Y-%m-%d')
        battles = elastic.search(index=index, body=battles_query)

        for bucket in battles['aggregations']['2']['buckets']:
            key = bucket['key_as_string'].split('T')[0]
            if not bucket['3']['buckets']:
                continue
            data = {}
            for subbucket in bucket['3']['buckets']:
                data[subbucket['key']] = subbucket['1']['value']
            with open('data/summary/battles/' + key + '.json', 'w') as f:
                dump(data, f)


def query_new_players(elastic, index, start, end=datetime.utcnow(), step=90):
    tr = timerange(start, end, step)
    for older, newer in tr:
        new_players_query['query']['bool'][
                'must'][-1]['range']['created_at']['gte'] = older.strftime('%Y-%m-%d')
        new_players_query['query']['bool'][
                'must'][-1]['range']['created_at']['lt'] = newer.strftime('%Y-%m-%d')
        new_players = elastic.search(index=index, body=new_players_query)

        for bucket in new_players['aggregations']['2']['buckets']:
            key = bucket['key_as_string'].split('T')[0]
            if not bucket['3']['buckets']:
                continue
            data = {}
            for subbucket in bucket['3']['buckets']:
                data[subbucket['key']] = subbucket['doc_count']
            with open('data/summary/new/' + key + '.json', 'w') as f:
                dump(data, f)


def query_min_5_a_day(elastic, index, start, end=datetime.utcnow(), step=90):
    tr = timerange(start, end, step)
    for older, newer in tr:
        five_battles_a_day_query['query']['bool'][
                'must'][-1]['range']['date']['gte'] = older.strftime('%Y-%m-%d')
        five_battles_a_day_query['query']['bool'][
                'must'][-1]['range']['date']['lte'] = newer.strftime('%Y-%m-%d')
        five_battles = elastic.search(index=index, body=five_battles_a_day_query)

        for bucket in five_battles['aggregations']['4']['buckets']:
            key = bucket['key_as_string'].split('T')[0]
            if not bucket['3']['buckets']:
                continue
            data = {}
            for subbucket in bucket['3']['buckets']:
                data[subbucket['key']] = subbucket['2']['buckets']['5.0-*']['doc_count']
            with open('data/summary/min5/' + key + '.json', 'w') as f:
                dump(data, f)


class ConvertTime(Action):
    def __call__(self, parser, namespace, values, default, option_string=None):
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
    agp.add_argument('-s', '--start', default=datetime(2014, 1, 1, 0, 0), action=ConvertTime, help='%Y-%m-%d format')
    agp.add_argument('-c', '--config', default='config.json')
    agp.add_argument('-e', '--end', default=datetime.utcnow(), action=ConvertTime, help='%Y-%m-%d format')
    agp.add_argument('--step', default=90)

    args = agp.parse_args()

    with open(args.config) as f:
        config = load(f)

    es = Elasticsearch(**config['elasticsearch'])

    query_active_accounts(es, config['es index'], args.start, args.end, args.step)
    query_battles(es, config['es index'], args.start, args.end, args.step)
    query_new_players(es, 'players', args.start, args.end, args.step)
    query_min_5_a_day(es, config['es index'], args.start, args.end, args.step)
