import json as json
import requests

crlist = []

urlcr = 'http://apfmon.lancs.ac.uk/mon/c'

cid='1234.0'
nick='ANALY_BHAM'
fid='voatlas171'
label='ANALY_BHAM'
d=(cid,nick,fid,label)

crlist.append(d)
j=json.JSONEncoder()
jmsg = j.encode(crlist)

r = requests.post('http://apfmon.lancs.ac.uk/mon/c', data=jmsg)
print 'OK?', r.ok
print 'TEXT:', r.text
