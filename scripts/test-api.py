import json
import random
import requests

crlist = []

baseuri = 'http://apfmon.lancs.ac.uk/api/'
urlcr = 'http://apfmon.lancs.ac.uk/mon/c'

cid=str(random.randint(1,10000))
nick='ANALY_BHAM'
fid='peter-uk-dev'
label='ANALY_BHAM'
d=(cid,nick,fid,label)

crlist.append(d)
j=json.JSONEncoder()
jmsg = j.encode(crlist)

r = requests.post(baseuri + 'c', data=jmsg)
print 'OK?', r.ok
print 'STATUS_CODE', r.status_code
print 'CONTENT-TYPE', r.headers['content-type']
#print 'TEXT:', r.text
