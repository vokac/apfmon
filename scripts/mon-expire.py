import logging
import pytz
import redis
import statsd
import sys
import time
from datetime import timedelta, datetime
from optparse import OptionParser
from pymongo import Connection
from django.conf import settings

r = redis.StrictRedis(host=settings.REDIS['host'], port=6379, db=0)

"""
Enforce various timeouts by moving jobs to FAULT state
"""

sys.path.append('/var/local/django')

from atl.mon.models import Job
from atl.mon.models import Message
from django.conf import settings
from django.core.cache import cache

def main():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option("-q", "--quiet",
                       dest="loglevel",
                       default=logging.WARNING,
                       action="store_const",
                       const=logging.WARNING,
                       help="Set logging level to WARNING [default]")
    parser.add_option("-v", "--info",
                       dest="loglevel",
                       default=logging.WARNING,
                       action="store_const",
                       const=logging.INFO,
                       help="Set logging level to INFO [default WARNING]")
    (options, args) = parser.parse_args()

    logger = logging.getLogger()
    logger.setLevel(options.loglevel)
    fmt = '[APFMON:%(levelname)s %(asctime)s] %(message)s'
    formatter = logging.Formatter(fmt, '%T')
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.handlers = []
    logger.addHandler(handler)

    ctimeout = 6
    rtimeout = 72
    etimeout = 30
    ftimeout = 48# 96

    # created state
    deltat = datetime.now(pytz.utc) - timedelta(hours=ctimeout)
    cjobs = Job.objects.filter(state='created', last_modified__lt=deltat, flag=False)
    logging.info("Stale created: %d" % cjobs.count())
    
    # running state
    deltat = datetime.now(pytz.utc) - timedelta(hours=rtimeout)
    rjobs = Job.objects.filter(state='running', last_modified__lt=deltat, flag=False)
    logging.info("Stale running: %d" % rjobs.count())
    
    # exiting state
    deltat = datetime.now(pytz.utc) - timedelta(minutes=etimeout)
    ejobs = Job.objects.filter(state='exiting', last_modified__lt=deltat)
    logging.info("Stale exiting: %d" % ejobs.count())
    
    # flagged jobs
    deltat = datetime.now(pytz.utc) - timedelta(hours=ftimeout)
    fjobs = Job.objects.filter(last_modified__lt=deltat, flag=True)
    logging.info("Stale flagged: %d" % fjobs.count())

    for j in cjobs:
        # flag stale created jobs
        if j.flag: continue
        logging.info(j.jid)
        msg = "In CREATED state >%dhrs so flagging the job" % ctimeout 
        element = "%f %s %s" % (time.time(), '127.0.0.1', msg)
        r.rpush(j.jid, element)
        j.flag = True
        j.save()

    for j in rjobs:
        # flag stale running jobs
        if j.flag: continue
        msg = "In RUNNING state >%dhrs so flagging the job" % rtimeout 
        element = "%f %s %s" % (time.time(), '127.0.0.1', msg)
        r.rpush(j.jid, element)
        j.flag = True
        j.save()

    for j in fjobs:
        # move flagged jobs to FAULT state
        msg = "Job flagged for >%dhrs so setting state to FAULT" % ftimeout
        element = "%f %s %s" % (time.time(), '127.0.0.1', msg)
        r.rpush(j.jid, element)
        j.state = fstate
        j.save()

    for j in ejobs:
        # move EXITING jobs to DONE state
        msg = "%s -> DONE" % j.state
        element = "%f %s %s" % (time.time(), '127.0.0.1', msg)
        r.rpush(j.jid, element)
        j.state = dstate
        j.save()

        key = "fex%d" % j.fid.id
        try:
            val = cache.decr(key)
        except ValueError:
            # key not known so set to current count
            msg = "MISS key: %s" % key
            logging.debug(msg)
            val = Job.objects.filter(fid=j.fid, state='exiting').count()
            added = cache.add(key, val)
            if added:
                msg = "Added DB count for key %s : %d" % (key, val)
                logging.debug(msg)
            else:
                msg = "Failed to decr key: %s" % key
                logging.debug(msg)

        key = "fdn%d" % j.fid.id
        try:
            val = cache.incr(key)
        except ValueError:
            # key not known so set to current count
            msg = "MISS key: %s" % key
            logging.debug(msg)
            val = Job.objects.filter(fid=j.fid, state='done').count()
            added = cache.add(key, val)
            if added:
                msg = "Added DB count for key %s : %d" % (key, val)
                logging.debug(msg)
            else:
                msg = "Failed to incr key: %s, db count: %d" % (key, val)
                logging.debug(msg)

if __name__ == "__main__":
#    connection = Connection('py-stor', 27017)
#    db = connection.jobdb
    c = statsd.StatsClient(settings.GRAPHITE['host'],
                           settings.GRAPHITE['port'])
    stat = 'apfmon.monexpire'
    start = time.time()
    rc = main()
    elapsed = time.time() - start
    c.timing(stat,int(elapsed))
    sys.exit(rc)
