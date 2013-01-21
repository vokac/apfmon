import json
import random
import requests

def result(r):
    print
    print 'OK?', r.ok
    print 'URL', r.url
    print 'STATUS_CODE', r.status_code
    print 'CONTENT-TYPE', r.headers['content-type']
    print 'LOCATION', r.headers['location']
    print 'TEXT:', r.text
    print '--------------------------------------------------'

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
print "TEST: PUT /jobs2 with payload defining individual jobs"
payload = [j1, j2]
url = baseuri + 'jobs2'
r = requests.put(url, data=json.dumps(payload))
result(r)

print "TEST: GET /jobs2/some-jobid of existing job"
jid = ':'.join(('peter-uk-dev',j2['cid']))
url = baseuri + '/'.join(('jobs2',jid))
r = requests.get(url)
result(r)

print "TEST: GET /jobs2 with params to refine the query"
url = baseuri + 'jobs2'
payload = {
        'factory' : 'peter-uk-dev',
        'state'   : 'exiting',
}
r = requests.get(url, params=payload)
result(r)

# /factories GET
url = baseuri + 'factories'
r = requests.get(url)
result(r)

print "TEST: GET /factories/some-factory of an existing factory"
url = baseuri + '/'.join(('factories',factory))
r = requests.get(url)
result(r)

print "TEST: GET /factories/some-factory of a non-existing factory"
url = baseuri + '/'.join(('factories','notme'))
r = requests.get(url)
result(r)

print "TEST: PUT /factories/some-new-factory non-existing factory"
factory = '-'.join(('new',str(random.randint(100,999))))
url = baseuri + '/'.join(('factories',factory))
f = {
     'url'     : 'http://localhost/',
     'email'   : 'p.love@lancaster.ac.uk',
     'version' : '0.0.1',
    }
r = requests.put(url, data=json.dumps(f))
result(r)

print "TEST: POST /jobs2/some-jobid?state=running to change job state"
jid = ':'.join(('peter-uk-dev',j2['cid']))
url = baseuri + '/'.join(('jobs2',jid))
payload = {'state' : 'exiting'}
r = requests.post(url, params=payload)
result(r)
