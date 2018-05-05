from __future__ import division
import requests
import json
from flask import Flask
from pymongo import MongoClient
from flask import jsonify
from flask_cors import CORS
from ConfigParser import SafeConfigParser
import os, time, datetime

# flask settings
app = Flask(__name__)
CORS(app)

# parser
parser = SafeConfigParser()
parser.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))

# mongodb
client = MongoClient('mongodb://localhost:27017/')
db_name = parser.get('DB', 'name')
db = client.db_name

# config
host = parser.get('Node', 'protocol') + parser.get('Node', 'ip') + parser.get('Node', 'port')
endpoint = parser.get('Node', 'getbalanceendpoint')
address = parser.get('Account', 'address')
getforgeddiff = parser.get('Node', 'getforgeddiff')
getdelegateinfo = parser.get('Node', 'getdelegateinfo')
pub_key = parser.get('Account', 'pub_key')
username = parser.get('Account', 'username')


def calc_pool_perc():
    """

    :return: pool % settings based on pool rank
    """

    r = requests.get(host + getdelegateinfo + username)
    rate = json.loads(r.text)['delegate']['rate']
    if rate >= 50:
        return float(parser.get('Pool', 'top_101_%'))
    if rate < 50 and rate >= 20:
        return float(parser.get('Pool', 'top_50_%'))
    if rate < 20:
        return float(parser.get('Pool', 'top_20_%'))


def calculate_voter_score(voter_days, voter_balance, voters):
    """

    :param voter_days:
    :param voter_balance:
    :param voters:
    :return: voter score
    """

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


def forged_from_last_payout():
    """

    :return: forged token since last payday
    """

    last_payout = db.payouts.find({}).sort([('date', -1)]).limit(1)
    r = requests.get(host + getforgeddiff.format(PUBLICKEY=pub_key, LAST_PAYOUT=str(last_payout[0]['date']), TODAY_PAYOUT=str(int(time.time()))))

    response = {'forged': int(json.loads(r.text)['forged']), 'last_pay_day': datetime.datetime.fromtimestamp(
        last_payout[0]['date']
    ).strftime('%d-%m-%Y')}

    return response


@app.route("/getforginginfo/<string:address>", methods=['GET'], endpoint='getforginginfo')
def get_forging_info(address):
    """

    :param address:
    :return: voter forging stats API
    """

    voters = db.voters
    voter = voters.find_one({'address': address})

    score = calculate_voter_score(voter['day_in_pool'], int(voter['balance']), voters)

    if (parser.get('Pool', 'dynamic_pool') == 'True'):
        perc_of_split = float(calc_pool_perc())
    else:
        perc_of_split = float(parser.get('Pool', 'static_%'))

    if 'pending_balance' in voter:
        pending_balance = int(voter['pending_balance'])
        balance = ((((forged_from_last_payout()['forged']) * perc_of_split) * score) + pending_balance) - 10000000
    else:
        pending_balance = 0
        balance = (((forged_from_last_payout()['forged']) * perc_of_split) * score) - 10000000


    if voter:
        output = {'address': voter['address'], 'score': score, 'earn': round(balance/100000000,3), 'days': voter['day_in_pool'],'pending_balance':round(pending_balance/100000000,3)}
    else:
        output = "No such name"
    return jsonify({'result': output})


@app.route("/getlastpayout/", methods=['GET'], endpoint='getlastpayout')
def get_last_payout_info():
    """

    :return: forged token since last payday API
    """

    forged = forged_from_last_payout()['forged']
    date = forged_from_last_payout()['last_pay_day']
    response = {'forged': forged, 'date': date}
    return jsonify({'result': response})


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', threaded=True)
