from __future__ import division
import os
import requests, json, logging
from ConfigParser import SafeConfigParser
from pymongo import MongoClient

logging.basicConfig(format='[%(asctime)s] %(message)s', filename='split-log.log', level=logging.INFO)

"""
MongoDB connection

"""

client = MongoClient('mongodb://localhost:27017/')
db = client.lisk_pool


"""
Parser config

"""

parser = SafeConfigParser()
parser.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))

"""
Lisk api endpoints

"""
host = parser.get('Node', 'protocol') + parser.get('Node', 'ip') + parser.get('Node', 'port')
getbalanceendpoint = parser.get('Node', 'getbalanceendpoint')
username = parser.get('Account', 'username')
address = parser.get('Account', 'address')
username = parser.get('Account', 'username')
paymentendpoint = parser.get('Node', 'paymentendpoint')
getdelegateinfo = parser.get('Node', 'getdelegateinfo')

""":
Calculate pool % based on rank
     
:return: float
"""

def calc_pool_perc():
    r = requests.get(host + getdelegateinfo + username)
    rate = json.loads(r.text)['delegate']['rate']
    if rate >= 50:
        return float(parser.get('Pool', 'top_101_%'))
    if rate < 50 and rate >= 20:
        return float(parser.get('Pool', 'top_50_%'))
    if rate < 20:
        return float(parser.get('Pool', 'top_20_%'))

""":
Calculate pool
    pool_days: sum of days in pool of each voter
    voters_tot_balance: sum of balance of each voter in pool
    totscore: score of the pool

:param collection: mongo voters collection 
:return: dict
"""

def calculate_total(collection):
    pool_days = 0
    voters_tot_balance = 0
    totscore = 0

    cursor = collection

    for v in cursor:
        pool_days += v['day_in_pool']
        voters_tot_balance += int(v['balance'])

    cursor.rewind()

    for i in cursor:
        i['score'] = (i['day_in_pool'] / pool_days) + (int(i['balance']) / voters_tot_balance)
        totscore += i['score']

    total = dict()
    total['pool_days'] = pool_days
    total['voters_tot_balance'] = voters_tot_balance
    total['totscore'] = totscore

    return total


"""
Calculate score of a single voter

:param voter_days: amount of voter days in pool  
:param pool_days: sum of voters days in pool
:param voter_balance: voter balance
:param voters_tot_balance: sum of voters balance in pool

:return: score for the single voter
"""


def calculate_score(voter_days, pool_days, voter_balance, voters_tot_balance):
    score = ((voter_days / pool_days) + (voter_balance / voters_tot_balance))
    return round(score, 3)

"""
Make payment API

:param address: voter address for payout  
:param amount: amount of pay

:return: string 
"""
def make_payment(address, amount):
    body = {}
    headers = {'Content-type': 'application/json'}
    body['secret'] = parser.get('Account', 'secret')
    body['publicKey'] = parser.get('Account','pub_key')
    if parser.get('Account', 'second_secret'):
        body['secondSecret'] = parser.get('Account', 'second_secret')
    body['amount'] = int(amount)
    body['recipientId'] = address
    response = requests.put(host+paymentendpoint, data=json.dumps(body), headers=headers)
    response = "payment for {} -> {}".format(
        address,
        json.loads(response.text)
    )
    return response

"""
Get pool balance API

:param address: voter address for payout  
:param amount: amount of pay

:return: pool balance 
"""
def get_current_balance():
    r = requests.get(host + getbalanceendpoint + address)
    return int(json.loads(r.text)['balance']) - int(parser.get('Pool', 'swap_holding'))

"""
Calculate voter payout

:param score: voter score  
:param balance: pool balance

:return: payment 
"""
def calculate_payment(score,balance,totscore):
    if(parser.get('Pool','dynamic_pool')):
        perc_of_split = float(calc_pool_perc())
    else:
        perc_of_split = float(parser.get('Pool','static_%'))

    payment = (score/totscore) * (balance*perc_of_split)
    return payment


voters_collection = db.voters
voters = voters_collection.find()

tot = calculate_total(voters)
forger_balance = get_current_balance()

voters.rewind()

for v in voters:
    if int(v['balance']) != 0:
        voter_score = calculate_score(v['day_in_pool'],tot['pool_days'],int(v['balance']),tot['voters_tot_balance'])

        if 'pending_balance' in v:
            to_pay = calculate_payment(voter_score,forger_balance,tot['totscore']) - 10000000 + int(v['pending_balance'])
        else:
            to_pay = calculate_payment(voter_score, forger_balance, tot['totscore']) - 10000000

        # if to pay > 1 LSK
        if to_pay > 100000000:
            # check if there is anny pending_balance
            if 'pending_balance' in v:
                db.voters.update(
                    {'address': v['address']},
                    {
                        '$set': {
                            'pending_balance': 0
                        }
                    },
                    True)
            # pay and stop
            res = make_payment(v['address'],to_pay)
            info_str = "{} paid".format(res)
            logging.info(info_str)
        else:
            # write pending db in database for that user
            db.voters.update(
                {'address': v['address']},
                {
                    '$set': {
                        'pending_balance': to_pay
                    }
                },
                True)
            info_str = "{} pending".format(v['address'])
            logging.info(info_str)