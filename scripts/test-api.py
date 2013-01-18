import json
import random
import requests

crlist = []

baseuri = 'http://apfmon.lancs.ac.uk/api/'
baseuri = 'http://py-dev.lancs.ac.uk:8000/api/'

nick = 'ANALY_LANCS-nick'
factory = 'peter-uk-dev'
label = 'ANALY_LANCS-label'

cid = str(random.randint(1,10000))
j1 = {
      'cid'     : cid,
      'nick'    : nick,
      'factory' : factory,
      'label'   : label,
    }

cid = str(random.randint(1,10000))
j2 = {
      'cid'     : cid,
      'nick'    : nick,
      'factory' : factory,
      'label'   : label,
    }

# payload is a list of dicts defining individual jobs
payload = [j1, j2]
url = baseuri + 'jobs2'
r = requests.put(url, data=json.dumps(payload))
print 'OK?', r.ok
print 'URL', r.url
print 'STATUS_CODE', r.status_code
print 'CONTENT-TYPE', r.headers['content-type']
print 'TEXT:', r.text

# /factories GET
url = baseuri + 'factories'
r = requests.get(url)
print 'OK?', r.ok
print 'URL', r.url
print 'STATUS_CODE', r.status_code
print 'CONTENT-TYPE', r.headers['content-type']
print 'TEXT:', r.text

print "TEST: GET /factories/some-factory of an existing factory"
url = baseuri + '/'.join(('factories',factory))
r = requests.get(url)
print 'OK?', r.ok
print 'URL', r.url
print 'STATUS_CODE', r.status_code
print 'CONTENT-TYPE', r.headers['content-type']
print 'TEXT:', r.text

print "TEST: GET /factories/some-factory of a non-existing factory"
url = baseuri + '/'.join(('factories','notme'))
r = requests.get(url)
print 'OK?', r.ok
print 'URL', r.url
print 'STATUS_CODE', r.status_code
print 'CONTENT-TYPE', r.headers['content-type']

print "TEST: PUT /factories/some-new-factory non-existing factory"
factory = '-'.join(('new',str(random.randint(100,999))))
url = baseuri + '/'.join(('factories',factory))
f = {
     'url'     : 'http://localhost/',
     'email'   : 'p.love@lancaster.ac.uk',
     'version' : '0.0.1',
    }
r = requests.put(url, data=json.dumps(f))
print 'OK?', r.ok
print 'URL', r.url
print 'STATUS_CODE', r.status_code
print 'CONTENT-TYPE', r.headers['content-type']
print 'TEXT:', r.text

print "TEST: GET /jobs/some-jobid of existing job"
jid = ':'.join(('peter-uk-dev',j2['cid']))
jid = ':'.join(('peter-uk-dev','1237017.0'))
url = baseuri + '/'.join(('jobs2',jid))
r = requests.get(url)
print 'OK?', r.ok
print 'URL', r.url
print 'STATUS_CODE', r.status_code
print 'CONTENT-TYPE', r.headers['content-type']
print 'TEXT:', r.text

