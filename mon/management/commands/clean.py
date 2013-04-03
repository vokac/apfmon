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
    help = 'Remove jobs from DB older than supllied time'
    logger = logging.getLogger(__name__)
#    logger.setLevel(options.loglevel)
    logger.setLevel(logging.info)

    def handle(self, *args, **options):
        t = int(args[0])
        dt = datetime.now(pytz.utc) - timedelta(hours=t)
        djobs = Job.objects.filter(state='done', last_modified__lt=dt)
        fjobs = Job.objects.filter(state='fault', last_modified__lt=dt)
        
        msg = 'DONE: %d' % djobs.count()
        logging.info(msg)
        msg = 'FAULT: %d' % fjobs.count()
        logging.info(msg)
        stats.gauge('apfmon.dclean',djobs.count())
        stats.gauge('apfmon.fclean',fjobs.count())
        djobs.delete()
        fjobs.delete()

        # remove messages from redis
        jobids = djobs.values_list('jid', flat=True)
        red.delete(jobids)
        jobids = fjobs.values_list('jid', flat=True)
        red.delete(jobids)

