import re
import sys

sys.path.append('/opt/panda/lib/python2.3/site-packages/')
from pandatools import Client

_SITEMATCH = re.compile('(\S+)_(\S+)')

(e,sitespec) = Client.getSiteSpecs(siteType='all')

for k,v in sitespec.items():
    if v['cloud'] == 'UK':
        sitematch = _SITEMATCH.match(v['ddm'])
        sitename = sitematch.group(1)
        q = '(SELECT id FROM pyf_site WHERE name="%s")' % sitename
        print "INSERT INTO pyf_pandasite (name,site_id) VALUES ('%s', %s);" % (v['sitename'], q)

