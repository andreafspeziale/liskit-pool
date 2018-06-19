from __future__ import division
import os, time, datetime, json, requests
from flask import Flask
from pymongo import MongoClient
from flask import jsonify
from flask_cors import CORS
from ConfigParser import SafeConfigParser

# flask settings
app = Flask(__name__)
CORS(app)

# parser
parser = SafeConfigParser()
parser.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))

# mongodb
client = MongoClient('mongodb://localhost:27017/')
db_name = parser.get('DB', 'name')
db = client[db_name]

# config
host = parser.get('Node', 'protocol') + parser.get('Node', 'ip') + parser.get('Node', 'port')
endpoint = parser.get('Node', 'getbalanceendpoint')
address = parser.get('Account', 'address')
getforgeddiff = parser.get('Node', 'getforgeddiff')
getdelegateinfo = parser.get('Node', 'getdelegateinfo')
pub_key = parser.get('Account', 'pub_key')
username = parser.get('Account', 'username')

transaction_cost = int(parser.get('Payments', 'cost'))
payment_threshold = int(parser.get('Payments', 'threshold'))

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
        # i['score'] = (i['day_in_pool']/pool_days) + (int(i['balance']) / voters_balance)
        i['score'] = (i['day_in_pool'] * int(i['balance'])) / (pool_days * voters_balance)
        totscore += i['score']

    score = (voter_days * voter_balance) / (pool_days * voters_balance)
    
    return {'score': round(score, 8), 'totscore': round(totscore, 8)}


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

    try:
        scoreandtot = calculate_voter_score(voter['day_in_pool'], int(voter['balance']), voters)
    except Exception as e:
        print 'Error'
        print e
        output = 'Not found'
        return jsonify({'result': output, 'success': False})
        
    score = scoreandtot['score']
    tot_score = scoreandtot['totscore']

    if (parser.get('Pool', 'dynamic_pool') == 'True'):
        perc_of_split = float(calc_pool_perc())
    else:
        perc_of_split = float(parser.get('Pool', 'static_%'))

    if 'pending_balance' in voter:
        pending_balance = int(voter['pending_balance'])
        balance = ((((forged_from_last_payout()['forged']) * perc_of_split) * (score / tot_score)) + pending_balance) # - transaction_cost
    else:
        pending_balance = 0
        balance = (((forged_from_last_payout()['forged']) * perc_of_split) * (score / tot_score)) - transaction_cost

    output = {
        'address': voter['address'],
        'voter_balance' : int(voter['balance']),
        'score': score, 
        'earn': round(balance/100000000,3), 
        'days': voter['day_in_pool'],
        'pending_payout':round(pending_balance/100000000,8),
        'transaction_cost': transaction_cost,
        'payment_threshold': payment_threshold,
        'pool_tot_score': tot_score
    }
    
    return jsonify({'result': output, 'success': True})


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
