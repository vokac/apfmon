from django.core.management.base import BaseCommand, CommandError, NoArgsCommand

from apfmon.mon.models import Factory
from apfmon.mon.models import Job
from apfmon.mon.models import Label
from django.conf import settings
from django.core.cache import cache
from django.conf import settings
from django.db.models import Count

import logging
import pytz
import redis
import statsd
import sys
import time
from datetime import timedelta, datetime
#from optparse import OptionParser
#from pymongo import Connection

"""
Get info about DB and print or publish to statsd
"""

red = redis.StrictRedis(host=settings.REDIS['host'], port=6379, db=0)

class Command(NoArgsCommand):
    args = '<...>'
    help = 'Enforce various timeouts by moving jobs to FAULT state'
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.debug)

    def handle(self, *args, **options):
        stats = statsd.StatsClient(settings.GRAPHITE['host'], settings.GRAPHITE['port'])
        
        flagcount = Job.objects.filter(flag=True).count()
        counts = Job.objects.values('state').annotate(n=Count('state'))

        labelcount = Label.objects.count()
        factorycount = Factory.objects.count()
        
        for c in counts:
            msg = 'Total %s count : %d' % (c['state'], c['n'])
#            self.stdout.write(msg+'\n')
            statname = 'apfmon.n%s' % c['state']
            stats.gauge(statname, c['n'])

        msg = 'Total flagged count : %s' % flagcount
#        self.stdout.write(msg+'\n')
        stats.gauge('apfmon.nflag', flagcount)


        msg = 'Total label count   : %s' % labelcount
#        self.stdout.write(msg+'\n')
        stats.gauge('apfmon.nlabel', labelcount)

        msg = 'Total factory count : %s' % factorycount
#        self.stdout.write(msg+'\n')
        stats.gauge('apfmon.nfactory', factorycount)
        
        vers = list(Factory.objects.values_list('version', flat=True))
        for v in set(vers): 
          stat = 'apfmon.factory.' + v.replace('.','_')
          stats.gauge(stat, vers.count(v))
