import statsd
from atl.mon.models import State
from atl.mon.models import Factory
from atl.mon.models import Job
from atl.mon.models import Label
from atl.mon.models import Message
from atl.mon.models import Pandaid

# http://statsd.readthedocs.org/en/latest/index.html
c = statsd.StatsClient('py-heimdallr', 8125)

jobcount = Job.objects.count()
labelcount = Label.objects.count()
factorycount = Factory.objects.count()

vers = list(Factory.objects.values_list('version', flat=True))
for v in set(vers): 
  stat = 'apfmon.factory.' + v
  print stat
  c.gauge(stat, vers.count(v))
