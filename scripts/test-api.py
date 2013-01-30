import json
import random
import requests

crlist = []

baseuri = 'http://py-dev.lancs.ac.uk:8123/api/'
baseuri = 'http://apfmon.lancs.ac.uk/api/'
urlcr = 'http://apfmon.lancs.ac.uk/mon/c'

nick = 'ANALY_LANCS'
factory = 'peter-uk-dev'
label = 'ANALY_LANCS-api'

jid = str(random.randint(1,10000))
j1 = {
      'jid'     : jid,
      'nick'    : nick,
      'factory' : factory,
      'label'   : label,
    }

jid = str(random.randint(1,10000))
j2 = {
      'jid'     : jid,
      'nick'    : nick,
      'factory' : factory,
      'label'   : label,
    }

# payload is a list of dicts defining individual jobs
payload = [j1, j2]
url = baseuri + 'jobs2'
r = requests.post(url, data=json.dumps(payload))
print 'OK?', r.ok
print 'URL', r.url
print 'STATUS_CODE', r.status_code
print 'CONTENT-TYPE', r.headers['content-type']
print 'TEXT:', r.text
