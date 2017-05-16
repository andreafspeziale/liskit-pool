from __future__ import division
import requests
import json
from flask import Flask
from pymongo import MongoClient
from flask import jsonify
from flask_cors import CORS
from ConfigParser import SafeConfigParser
import os

app = Flask(__name__)
CORS(app)

parser = SafeConfigParser()
parser.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))

client = MongoClient('mongodb://localhost:27017/')
db = client.lisk_pool

host = parser.get('Node', 'protocol') + parser.get('Node', 'ip') + parser.get('Node', 'port')
endpoint = parser.get('Node', 'getbalanceendpoint')
address = parser.get('Account', 'address')

getdelegateinfo = parser.get('Node', 'getdelegateinfo')
pub_key = parser.get('Account', 'pub_key')
username = parser.get('Account', 'username')
getdelegateinfo = parser.get('Node', 'getdelegateinfo')

def calc_pool_perc():
    r = requests.get(host + getdelegateinfo + username)
    rate = json.loads(r.text)['delegate']['rate']
    if rate >= 50:
        return float(parser.get('Pool', 'top_101_%'))
    if rate < 50 and rate >= 20:
        return float(parser.get('Pool', 'top_50_%'))
    if rate < 20:
        return float(parser.get('Pool', 'top_20_%'))

def calculate_voter_score(voter_days, voter_balance, voters):
    cursor = voters.find({})

    pool_days = 0
    voters_balance = 0
    totscore = 0

    for v in cursor:
        pool_days += v['day_in_pool']
        voters_balance += int(v['balance'])

    cursor = voters.find({})

    for i in cursor:
        i['score'] = (i['day_in_pool']/pool_days) + (int(i['balance']) / voters_balance)
        totscore += i['score']

    score = ((voter_days/pool_days) + (voter_balance / voters_balance))/totscore

    return round(score, 3)


def get_current_pool_balance():

    r = requests.get(host + endpoint + address)

    balance = json.loads(r.text)['balance']

    return int(balance)-int(parser.get('Pool', 'swap_holding'))


@app.route("/getforginginfo/<string:address>", methods=['GET'])
def get_forging_info(address):

    # How much is earning in each payout
    # He's scoreboard
    # Days in pool

    # There is also myself as voter

    voters = db.voters
    voter = voters.find_one({'address': address})

    score = calculate_voter_score(voter['day_in_pool'], int(voter['balance']), voters)

    if (parser.get('Pool', 'dynamic_pool')):
        perc_of_split = float(calc_pool_perc())
    else:
        perc_of_split = float(parser.get('Pool', 'static_%'))

    if 'pending_balance' in voter:
        pending_balance = int(voter['pending_balance'])
        balance = (((get_current_pool_balance() * perc_of_split) * score) + pending_balance) - 10000000
    else:
        pending_balance = 0
        balance = ((get_current_pool_balance() * perc_of_split) * score) - 10000000


    if voter:
        output = {'address': voter['address'], 'score': score, 'earn': round(balance/100000000,3), 'days': voter['day_in_pool'],'pending_balance':round(pending_balance/100000000,3)}
    else:
        output = "No such name"
    return jsonify({'result': output})

if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0')
