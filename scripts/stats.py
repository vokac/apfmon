import statsd
import sys

sys.path.append('/var/local/django')

from atl.mon.models import State
from atl.mon.models import Factory
from atl.mon.models import Job
from atl.mon.models import Label
from atl.mon.models import Message
#from atl.mon.models import Pandaid
from django.conf import settings
from django.db.models import Count

"""
Get info about DB and print or publish to statsd
"""

# http://statsd.readthedocs.org/en/latest/index.html
c = statsd.StatsClient(settings.GRAPHITE['host'], settings.GRAPHITE['port'])

jobcount = Job.objects.count()
flagcount = Job.objects.filter(flag=True).count()
msgcount = Message.objects.count()
labelcount = Label.objects.count()
factorycount = Factory.objects.count()

print 'Total job count     : ', jobcount
c.gauge('apfmon.njob', jobcount)
print 'Total flagged count : ', flagcount
c.gauge('apfmon.nflag', flagcount)
print 'Total msg count     : ', msgcount
c.gauge('apfmon.nmsg', msgcount)
print 'Total label count   : ', labelcount
c.gauge('apfmon.nlabel', labelcount)
print 'Total factory count : ', factorycount
c.gauge('apfmon.nfactory', factorycount)


## this is a slow query
#counts = Job.objects.values('state__name').annotate(count=Count('id'))
#for count in counts:
#  print count['state__name'], ':', count['count']

vers = list(Factory.objects.values_list('version', flat=True))
for v in set(vers): 
  stat = 'apfmon.factory.' + v.replace('.','_')
  print stat, vers.count(v)
  c.gauge(stat, vers.count(v))

