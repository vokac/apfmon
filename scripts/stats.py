import statsd
from atl.mon.models import State
from atl.mon.models import Factory
from atl.mon.models import Job
from atl.mon.models import Label
from atl.mon.models import Message
from atl.mon.models import Pandaid
from django.db.models import Count

"""
Get info about DB and print or publish to statsd
"""

# http://statsd.readthedocs.org/en/latest/index.html
c = statsd.StatsClient(host='py-heimdallr', port=8125)

jobcount = Job.objects.count()
msgcount = Message.objects.count()
labelcount = Label.objects.count()
factorycount = Factory.objects.count()

print 'Total job count    : ', jobcount
print 'Total msg count    : ', msgcount
print 'Total label count  : ', labelcount
print 'Total factory count: ', factorycount


counts = Job.objects.values('state__name').annotate(count=Count('id'))

for count in counts:
  print count['state__name'], ':', count['count']

vers = list(Factory.objects.values_list('version', flat=True))
for v in set(vers): 
  stat = 'apfmon.factory.' + v.replace('.','_')
  print stat, vers.count(v)
  c.gauge(stat, vers.count(v))

