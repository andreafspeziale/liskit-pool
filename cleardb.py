# Will remove from my database all vote swappers, gdt and elite members so all the shared funds go to the community

import os, logging, requests, json
from ConfigParser import SafeConfigParser
from pymongo import MongoClient

# parser
parser = SafeConfigParser()
parser.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))

# mongodb
client = MongoClient('mongodb://localhost:27017/')
db_name = parser.get('DB', 'name')
db = client[db_name]

# logging
logging.basicConfig(format='[%(asctime)s] %(message)s', filename='clear-log.log', level=logging.INFO)

# array of gdt and elite
gdt = parser.get('Skip', 'gdt')
elite = gdt = parser.get('Skip', 'elite')
swap = []

# db voters
db_voters_collection = db.voters
db_voters = db_voters_collection.find()

# request
# config
host = parser.get('Node','protocol')+parser.get('Node','ip')+parser.get('Node','port')
getvotesendpoint = parser.get('Node','getvotesendpoint')
address = parser.get('Account','address')

# my votes
def get_who_i_vote():
    r = requests.get(host + getvotesendpoint + address)
    votes = json.loads(r.text)['delegates']
    global swap 
    swap = [v['address'] for v in votes]

# clear db
def clear_db():
    counter = 0
    # for every already voter
    for v in db_voters:
        #if voter has swap, is gdt or elite
        if v['address'] in gdt or v['address'] in elite or v['address'] in swap:
            info_str = '{} delete'.format(v['address'])
            logging.info(info_str)
            # delete from db
            db_voters_collection.remove({'_id': v['_id']})
            counter+= 1
    info_str = '{} deleted'.format(counter)
    logging.info(info_str)

get_who_i_vote()
clear_db()