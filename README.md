# lisk-pool

> Thanks to [blubecks](https://github.com/blubecks) for the inputs.
> Thanks to [dakk](https://github.com/dakk) for the inputs. 

> With love by liskit (donations @ 10310263204519541551L) delegate

liskit-pool back-end. Attached to my [liskit-dashboard](https://github.com/andreafspeziale/liskit-dashboard) repository. Deployed at [liskit.me](https://liskit.me)

## Install 

    virtualenv env
    source env/bin/activate
    pip install -r requirements.txt

## Configuration

    cp config.ini.sample in config.ini

Edit it with your infos (e.g node ip, ...)
 
    config.ini

# Collect.py
Every minute/two minutes depending on your crontab config takes delegate voters:

if voter already present --> update values
if voter not present --> create voter
if voter removed vote --> remove voter

# Main.py
It is a flask simple server exposing one open API 

    - getforginginfo (e.g https://api.lisk.liskit.me/getforginginfo/address)
    
Sending the address of the voter it calculate the score and the next payout.
It is also used by the telegram [liskitbot](https://github.com/andreafspeziale/liskitbot) (@LiskitBot)

# Split.py
Get all the voters from the populated mongoDB (by collect.py) and calculate each voter payout and make it.

# Additional
The pool can also handle dynamic share % based on your rank.

# Deploy 
I would suggest the following configuratior for the apache2 deploy

## Folders
At `/var/www/delegate-pool/`:

- delegate-pool.wsgi

```
#!/usr/bin/python
activate_this = '/var/www/delegate-pool/pool/env/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))
import sys
import logging
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,"/var/www/delegate-pool/")

from pool import app as application
```

- pool folder

So at `/var/www/delegate-pool/pool`:

- collect.py
- config.ini
- env/
- __init__.py (it is the main.py)
- requirements.txt
- split.py

The virtualhost:

```
<VirtualHost *:80>
    ServerName api.delegate.me (based on your dns)

    WSGIScriptAlias / /var/www/delegate-pool/delegate-pool.wsgi

    <Directory /var/www/delegate-pool/pool/>
        Order allow,deny
        Allow from all
    </Directory>
    ErrorLog ${APACHE_LOG_DIR}/delegate-pool-error.log
    LogLevel warn
    CustomLog ${APACHE_LOG_DIR}/access.log combined
RewriteEngine on
RewriteCond %{SERVER_NAME} =api.delegate.me (based on your dns)
RewriteRule ^ https://%{SERVER_NAME}%{REQUEST_URI} [END,NE,R=permanent]
</VirtualHost>
```

# ToDo

- move all to python3