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

red = redis.StrictRedis(host=settings.REDIS['host'], port=6379, db=0)

class Command(NoArgsCommand):
    args = '<...>'
    help = 'Enforce various timeouts by moving jobs to FAULT state'
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.info)

    def handle(self, *args, **options):
            ctimeout = 6
            rtimeout = 72
            etimeout = 630
            ftimeout = 24# 96
        
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
            fjobs = Job.objects.filter(last_modified__lt=deltat, flag=True)
            self.logger.info("Stale flagged: %d" % fjobs.count())
        
            for j in cjobs[:20000]:
                # flag stale created jobs
                if j.flag: continue
                self.logger.info(j.jid)
                msg = "In CREATED state >%dhrs so flagging the job" % ctimeout 
                element = "%f %s %s" % (time.time(), '127.0.0.1', msg)
                red.rpush(j.jid, element)
                j.flag = True
                j.save()
        
            for j in rjobs:
                # flag stale running jobs
                if j.flag: continue
                msg = "In RUNNING state >%dhrs so flagging the job" % rtimeout 
                element = "%f %s %s" % (time.time(), '127.0.0.1', msg)
                red.rpush(j.jid, element)
                j.flag = True
                j.save()
        
            for j in fjobs:
                # move flagged jobs to FAULT state
                msg = "Job flagged for >%dhrs so setting state to FAULT" % ftimeout
                self.logger.debug(msg)
                element = "%f %s %s" % (time.time(), '127.0.0.1', msg)
                red.rpush(j.jid, element)
                j.state = 'fault'
                j.save()
        
            for j in ejobs:
                # move EXITING jobs to DONE state
                msg = "%s -> DONE" % j.state
                self.logger.debug(msg)
                element = "%f %s %s" % (time.time(), '127.0.0.1', msg)
                red.rpush(j.jid, element)
                j.state = 'done'
                j.save()

            self.logger.info('stale created:', len(cjobs))
            self.logger.info('stale running:', len(rjobs))
            self.logger.info('flag->fault:', len(fjobs))
            self.logger.info('exiting->done:', len(ejobs))
#if __name__ == "__main__":
##    connection = Connection('py-stor', 27017)
##    db = connection.jobdb
#    c = statsd.StatsClient(settings.GRAPHITE['host'],
#                           settings.GRAPHITE['port'])
#    stat = 'apfmon.monexpire'
#    start = time.time()
#    rc = main()
#    elapsed = time.time() - start
#    c.timing(stat,int(elapsed))
#    sys.exit(rc)
