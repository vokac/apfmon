from datetime import timedelta, datetime
import logging
import pytz
from optparse import OptionParser
import sys

sys.path.append('/var/local/django')

from atl.mon.models import Job
from atl.mon.models import Message
from atl.mon.models import State
#from atl.mon.models import Factory
from django.core.cache import cache

def main():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option("-q", action="store_true", default=False,
                      help="quiet mode", dest="quiet")
    parser.add_option("-d", action="store_true", default=False,
                      help="debug mode", dest="debug")
    (options, args) = parser.parse_args()
    if len(args) != 0:
        parser.error("incorrect number of arguments")
        return 1
    loglevel = 'INFO'
    if options.quiet:
        loglevel = 'WARNING'
    if options.debug:
        loglevel = 'DEBUG'

    logger = logging.getLogger()
    logger.setLevel(logging._levelNames[loglevel])
    fmt = '[MON:%(levelname)s %(asctime)s] %(message)s'
    formatter = logging.Formatter(fmt, '%T')
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.handlers = []
    logger.addHandler(handler)

    cstate = State.objects.get(name='CREATED')
    rstate = State.objects.get(name='RUNNING')
    estate = State.objects.get(name='EXITING')
    dstate = State.objects.get(name='DONE')
    fstate = State.objects.get(name='FAULT')
    
    deltat = datetime.now(pytz.utc) - timedelta(hours=6)
    cjobs = Job.objects.filter(state=cstate, last_modified__lt=deltat)
    logging.info("created: %d" % cjobs.count())
    
    deltat = datetime.now(pytz.utc) - timedelta(hours=48)
    rjobs = Job.objects.filter(state=rstate, last_modified__lt=deltat)
    logging.info("running: %d" % rjobs.count())
    
    deltat = datetime.now(pytz.utc) - timedelta(minutes=30)
    ejobs = Job.objects.filter(state=estate, last_modified__lt=deltat)
    logging.info("exiting: %d" % ejobs.count())
    
    skey = {'CREATED' : 'fcr',
            'RUNNING' : 'frn',
            'EXITING' : 'fex',
            }

    jobs = []
    jobs.extend(cjobs)
    jobs.extend(rjobs)
    for j in jobs:
        statenow = j.state
        msg = "%s -> FAULT, stale job" % statenow
        m = Message(job=j, msg=msg, client="127.0.0.1")
        m.save()
        msg = "%s_%s: %s -> FAULT, stale job" % (j.fid.name, j.cid, j.state)
        logging.debug(msg)
        j.state = fstate
        j.save()

        prefix = skey[statenow.name]
        key = "%s%d" % (prefix, j.fid.id)
        try:
            val = cache.decr(key)
        except ValueError:
            # key not known so set to current count
            msg = "MISS key: %s" % key
            logging.debug(msg)
            val = Job.objects.filter(fid=j.fid, state=statenow).count()
            added = cache.add(key, val)
            if added:
                msg = "Added DB count for key %s : %d" % (key, val)
                logging.debug(msg)
            else:
                msg = "Failed to decr key: %s" % key
                logging.debug(msg)

        key = "fft%d" % j.fid.id
        try:
            val = cache.incr(key)
        except ValueError:
            # key not known so set to current count
            msg = "MISS key: %s" % key
            logging.debug(msg)
            val = Job.objects.filter(fid=j.fid, state=fstate).count()
            added = cache.add(key, val)
            if added:
                msg = "Added DB count for key %s : %d" % (key, val)
                logging.debug(msg)
            else:
                msg = "Failed to incr key: %s" % key
                logging.debug(msg)


    for j in ejobs:
        msg = "%s -> DONE" % j.state
        m = Message(job=j, msg=msg, client="127.0.0.1")
        m.save()
        msg = "%s_%s: %s -> DONE" % (j.fid.name, j.cid, j.state)
        logging.debug(msg)
        j.state = dstate
        j.save()


        key = "fex%d" % j.fid.id
        try:
            val = cache.decr(key)
        except ValueError:
            # key not known so set to current count
            msg = "MISS key: %s" % key
            logging.debug(msg)
            val = Job.objects.filter(fid=j.fid, state=estate).count()
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
            val = Job.objects.filter(fid=j.fid, state=dstate).count()
            added = cache.add(key, val)
            if added:
                msg = "Added DB count for key %s : %d" % (key, val)
                logging.debug(msg)
            else:
                msg = "Failed to incr key: %s, db count: %d" % (key, val)
                logging.debug(msg)

if __name__ == "__main__":
    sys.exit(main())
