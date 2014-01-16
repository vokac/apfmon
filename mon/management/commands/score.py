"""
Update redis sorted set with queue scores
Scores are defined as:
100*fault/(done+fault) * log(created)
"""

from django.core.management.base import BaseCommand, CommandError, NoArgsCommand
from apfmon.mon.models import Job, Label
from django.conf import settings
from django.core.cache import cache

import logging
import pytz
import re
import redis
import requests
import socket
import statsd
import sys
import time
from datetime import timedelta, datetime
#from optparse import OptionParser

red = redis.StrictRedis(host=settings.REDIS['host'],
                        port=settings.REDIS['port'], db=0)
stats = statsd.StatsClient(settings.GRAPHITE['host'],
                           settings.GRAPHITE['port'])
expire2days = 172800
expire5days = 432000
expire7days = 604800

class Command(NoArgsCommand):
    args = '<...>'
    help = 'Update redis sorted set with queue scores'
    logger = logging.getLogger('apfmon.mon')

    def handle(self, *args, **options):
            start = time.time()
        
            # find job in created state older than ctimeout
            deltat = datetime.now(pytz.utc) - timedelta(minutes=120)
            
#            labels = Label.objects.filter(name__startswith='UKI')
            labels = Label.objects.filter(last_modified__gt=deltat)
            for label in labels:
                labelurl = '/'.join(('http://apfmon.lancs.ac.uk',
                                   label.fid.name,
                                   label.name))
                                

                cjobs = Job.objects.filter(label=label, state='created')
                score = cjobs.count()
                member = ':'.join((label.fid.name, label.name))
                red.zadd('score', score, member)
                msg = '%s: %s' % (label.name, score)
                self.logger.info(msg)
        
            elapsed = time.time() - start
