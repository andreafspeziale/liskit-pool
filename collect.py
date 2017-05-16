import requests, json, datetime,logging
from ConfigParser import SafeConfigParser
from pymongo import MongoClient
import os

client = MongoClient('mongodb://localhost:27017/')
db = client.lisk_pool

parser = SafeConfigParser()
parser.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))

logging.basicConfig(format='[%(asctime)s] %(message)s', filename='collect-log.log', level=logging.INFO)

host = parser.get('Node','protocol')+parser.get('Node','ip')+parser.get('Node','port')
getvotersendpoint = parser.get('Node','getvotersendpoint')
pub_key = parser.get('Account','pub_key')


def check_time_diff(last_update):
    """
    Return True if more than 24 hours has passed from last update

    :param last_update: 
    :param now: 
    :return: boolean 
    """

    now = datetime.datetime.now()

    return now.day != last_update.day


r = requests.get(host + getvotersendpoint + pub_key)

voters = json.loads(r.text)['accounts']
voters_already_in_pool = db.voters

# diff is the collection of voters that are already in the pool but have removed their vote
voters_public_keys = map(lambda y: y['publicKey'], voters)
voters_already_in_pool.remove({'publicKey':{'$nin':voters_public_keys}})

for v in voters:
    voter = voters_already_in_pool.find_one({'address': v['address']})
    if voter:
        if not check_time_diff(voter['updated_at']):
            #print 'no update day in pool'
            db.voters.update(
                {'address': v['address']},
                {'$set': {
                    'updated_at': datetime.datetime.now(),
                    'balance': v['balance']
                    }
                },
                True)
            info_str = '{} day in pool not updated'.format(v['username'])
        else:
            #print 'update day in pool'
            db.voters.update(
                {'address': v['address']},
                {
                    '$inc': {'day_in_pool': 1},
                    '$set': {
                        'updated_at': datetime.datetime.now(),
                        'balance': v['balance']
                    }

                },
                True)
            info_str = '{} day in pool updated'.format(v['username'])
    else:
        db.voters.insert_one({
            'address': v['address'],
            'day_in_pool': 1,
            'updated_at': datetime.datetime.now(),
            'username': v['username'],
            'publicKey': v['publicKey'],
            'balance': v['balance']
        })
        info_str = '{} welcome'.format(v['username'])
    logging.info(info_str)

