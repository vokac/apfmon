from django.core.management.base import BaseCommand, CommandError, NoArgsCommand
from apfmon.mon.models import Job
from django.conf import settings
from django.core.cache import cache

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
Remove jobs from DB which have been in DONE/FAULT state for
a set number of hours
"""

red = redis.StrictRedis(host=settings.REDIS['host'], port=6379, db=0)

stats = statsd.StatsClient(settings.GRAPHITE['host'],
                           settings.GRAPHITE['port'])

class Command(BaseCommand):
    args = '<hours>'
    help = 'Remove jobs from DB older than supplied time'
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.debug)

    def handle(self, *args, **options):
        t = int(args[0])
        dt = datetime.now(pytz.utc) - timedelta(hours=t)
        djobs = Job.objects.filter(state='done', last_modified__lt=dt)
        fjobs = Job.objects.filter(state='fault', last_modified__lt=dt)
        ndone = djobs.count()
        nfault = fjobs.count()
        start = time.time()
        
        msg = 'DONE: %d' % ndone
#        self.stdout.write(msg+'\n')
        msg = 'FAULT: %d' % nfault
#        self.stdout.write(msg+'\n')
        djobs.delete()
        fjobs.delete()

        # remove messages from redis
        jobids = djobs.values_list('jid', flat=True)
        red.delete(jobids)
        jobids = fjobs.values_list('jid', flat=True)
        red.delete(jobids)

        elapsed = time.time() - start
#        self.stdout.write(str(int(1000*elapsed))+'\n')
        stats.timing('apfmon.clean',int(1000*elapsed))
        stats.gauge('apfmon.dclean',ndone)
        stats.gauge('apfmon.fclean',nfault)
