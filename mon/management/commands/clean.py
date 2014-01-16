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
a set number of minutes
"""

red = redis.StrictRedis(host=settings.REDIS['host'], port=6379, db=0)

stats = statsd.StatsClient(settings.GRAPHITE['host'],
                           settings.GRAPHITE['port'])

class Command(BaseCommand):
    args = '<minutes>'
    help = 'Remove jobs from DB older than supplied time'
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.debug)

    def handle(self, *args, **options):
        t = int(args[0])
        dt = datetime.now(pytz.utc) - timedelta(minutes=t)
        djobs = Job.objects.filter(state='done', last_modified__lt=dt)
        fjobs = Job.objects.filter(state='fault', last_modified__lt=dt)
        start = time.time()
        
        # remove these joblog:jid keys (job messages)
        djobids = list(djobs.values_list('jid', flat=True))
        fjobids = list(fjobs.values_list('jid', flat=True))
        keylist = []
        for j in djobids+fjobids:
            key = ':'.join(('joblog',j))
            keylist.append(key)
        red.delete(keylist)

        # remove jid from done:label set
        for j in djobs:
            key = ':'.join(('done',j.label.fid.name,j.label.name))
            red.srem(key, j)
            
        # remove jid from fault:label set
        for j in fjobs:
            key = ':'.join(('fault',j.label.fid.name,j.label.name))
            red.srem(key, j)

        ndone = djobs.count()
        nfault = fjobs.count()
        msg = 'DONE: %d' % ndone
        msg = 'FAULT: %d' % nfault
        djobs.delete()
        fjobs.delete()

        elapsed = time.time() - start
#        self.stdout.write(str(int(1000*elapsed))+'\n')
        stats.timing('apfmon.clean',int(1000*elapsed))
        stats.gauge('apfmon.dclean',ndone)
        stats.gauge('apfmon.fclean',nfault)
