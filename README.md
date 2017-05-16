# lisk-pool

> Thanks to [blubecks](https://github.com/blubecks) for the inputs. 

> With love by liskit (donations @ 10310263204519541551L) delegate

## installation 

    virtualenv env
    source env/bin/activate
    pip install -r requirements.txt

## configuration

    cp config.ini.sample in config.ini

Edit it with your infos
 
    config.ini

# Collect.py
Every minute takes delegate voters:

if voter already present --> update values
if voter not present --> create voter
if voter removed vote --> remove voter

# Main.py
It is a flask simple server exposing one api 

    - getforginginfo
    
Sending the address of the voter it calculate the score and the next payout

# Split.py
Get all the voters from the populated mongoDB (by collect.py) and calculate each voter payout and make it.

# ToDo

✓ save for each voter that are not receiving the payout the amount they should receive and add it at the next payout

✓ delete from mongo DB the voters who removed the vote

✓ make rank reward dynamic

✓ remove personal 60K sub to balance from almost everywhere

✓ align with front-end repository and go open source
