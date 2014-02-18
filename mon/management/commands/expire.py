"""
Using the given timeouts, set flags and move jobs to final states.

"""

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

red = redis.StrictRedis(host=settings.REDIS['host'],
                        port=settings.REDIS['port'], db=0)
stats = statsd.StatsClient(settings.GRAPHITE['host'],
                           settings.GRAPHITE['port'])

class Command(NoArgsCommand):
    args = '<...>'
    help = 'Enforce various timeouts by moving jobs to FAULT state'
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.debug)

    def handle(self, *args, **options):
            ctimeout = 6
            rtimeout = 72
            etimeout = 30
            ftimeout = 24# 96
            expire2days = 172800
            expire3days = 259200
            expire5days = 432000
            expire7days = 604800
            start = time.time()
            nonterminal = ['created', 'running', 'exiting']
            terminal = ['done', 'fault']
        
            # created state
            deltat = datetime.now(pytz.utc) - timedelta(hours=ctimeout)
            cjobs = Job.objects.filter(state='created', last_modified__lt=deltat, flag=False)
            self.logger.info("Stale created: %d" % cjobs.count())
            
            # running state
            deltat = datetime.now(pytz.utc) - timedelta(hours=rtimeout)
            rjobs = Job.objects.filter(state='running', last_modified__lt=deltat, flag=False)
            self.logger.info("Stale running: %d" % rjobs.count())
            
            # exiting state
            deltat = datetime.now(pytz.utc) - timedelta(minutes=etimeout)
            ejobs = Job.objects.filter(state='exiting', last_modified__lt=deltat)
            self.logger.info("Stale exiting: %d" % ejobs.count())
            
            # flagged jobs
            deltat = datetime.now(pytz.utc) - timedelta(hours=ftimeout)
            fjobs = Job.objects.filter(state__in=nonterminal,last_modified__lt=deltat, flag=True)
            self.logger.info("Stale flagged: %d" % fjobs.count())
        
            # remove this once handled elsewhere
            for j in cjobs[:500]:
                # flag stale created jobs
                if j.flag: continue
                self.logger.info(j.jid)
                msg = "In CREATED state >%dhrs so flagging the job" % ctimeout 
                element = "%f %s %s" % (time.time(), '127.0.0.1', msg)
                key = ':'.join(('joblog',j.jid))
                red.rpush(key, element)
                red.expire(key, expire5days)
                j.flag = True
                j.save()
        
            for j in rjobs[:500]:
                # flag stale running jobs
                if j.flag: continue
                msg = "In RUNNING state >%dhrs so flagging the job" % rtimeout 
                element = "%f %s %s" % (time.time(), '127.0.0.1', msg)
                key = ':'.join(('joblog',j.jid))
                red.rpush(key, element)
                red.expire(key, expire5days)
                j.flag = True
                j.save()
        
            for j in ejobs[:500]:
                # move EXITING jobs to DONE state
                msg = "State change: %s -> done" % j.state
                self.logger.debug(msg)
                j.state = 'done'
                j.save()
                element = "%f %s %s" % (time.time(), '127.0.0.1', msg)
                key = ':'.join(('joblog',j.jid))
                red.rpush(key, element)
                red.expire(key, expire3days)
                # add jobid to the done set
                key = ':'.join(('done',j.label.fid.name,j.label.name))
                red.sadd(key,j.jid)
                red.expire(key,expire7days)

            for j in fjobs[:500]:
                # move flagged jobs to FAULT state
                msg = "Job flagged for >%dhrs so setting state to FAULT" % ftimeout
                self.logger.debug(msg)
                j.state = 'fault'
                j.save()
                element = "%f %s %s" % (time.time(), '127.0.0.1', msg)
                key = ':'.join(('joblog',j.jid))
                red.rpush(key, element)
                red.expire(key, expire3days)
                # add jobid to the fault set
                key = ':'.join(('fault',j.label.fid.name,j.label.name))
                red.sadd(key,j.jid)
                red.expire(key,expire7days)
        
            msg = 'stale created: %d' % len(cjobs)
            self.logger.info(msg)
            msg = 'stale running: %d' % len(rjobs)
            self.logger.info(msg)
            msg = 'flag->fault: %d' % len(fjobs)
            self.logger.info(msg)
            msg = 'exiting->done: %d' % len(ejobs)
            self.logger.info(msg)

            elapsed = time.time() - start
            stats.timing('apfmon.expire',int(1000*elapsed))
