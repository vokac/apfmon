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
        c = statsd.StatsClient(settings.GRAPHITE['host'], settings.GRAPHITE['port'])
        
        jobcount = Job.objects.count()
        flagcount = Job.objects.filter(flag=True).count()
        labelcount = Label.objects.count()
        factorycount = Factory.objects.count()
        
        msg = 'Total job count     : %s' % jobcount
        self.logger.info(msg)
        c.gauge('apfmon.njob', jobcount)

        msg = 'Total flagged count : %s' % flagcount
        self.logger.info(msg)
        c.gauge('apfmon.nflag', flagcount)

        msg = 'Total label count   : %s' % labelcount
        self.logger.info(msg)
        c.gauge('apfmon.nlabel', labelcount)

        msg = 'Total factory count : %s' % factorycount
        self.logger.info(msg)
        c.gauge('apfmon.nfactory', factorycount)
        
        
        ## this is a slow query
        #counts = Job.objects.values('state__name').annotate(count=Count('id'))
        #for count in counts:
        #  print count['state__name'], ':', count['count']
        
        vers = list(Factory.objects.values_list('version', flat=True))
        for v in set(vers): 
          stat = 'apfmon.factory.' + v.replace('.','_')
          c.gauge(stat, vers.count(v))
        
