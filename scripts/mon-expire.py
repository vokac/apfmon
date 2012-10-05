import logging
import pytz
import statsd
import sys
from datetime import timedelta, datetime
from optparse import OptionParser
from pymongo import Connection
from time import time


#
##collection = db.jobs
#
#job = {'name' : 'some-job-id',
#       'msgs' : [ {'received' : 'somedate', 'msg' : 'some message', 'client' : 'some IP'},
#                  {'received' : 'somedate', 'msg' : 'some message', 'client' : 'some IP'},
#                ]
#}
#
#db.jobs.insert(job);
#

"""
Enforce various timeouts by moving jobs to FAULT state
"""

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
    
    ctimeout = 6
    rtimeout = 72
    etimeout = 30
    ftimeout = 96

    # created state
    deltat = datetime.now(pytz.utc) - timedelta(hours=ctimeout)
    cjobs = Job.objects.filter(state=cstate, last_modified__lt=deltat, flag=False)
    logging.info("Stale created: %d" % cjobs.count())
    
    # running state
    deltat = datetime.now(pytz.utc) - timedelta(hours=rtimeout)
    rjobs = Job.objects.filter(state=rstate, last_modified__lt=deltat, flag=False)
    logging.info("Stale running: %d" % rjobs.count())
    
    # exiting state
    deltat = datetime.now(pytz.utc) - timedelta(minutes=etimeout)
    ejobs = Job.objects.filter(state=estate, last_modified__lt=deltat)
    logging.info("Stale exiting: %d" % ejobs.count())
    
    # flagged jobs
    deltat = datetime.now(pytz.utc) - timedelta(hours=ftimeout)
    fjobs = Job.objects.filter(flag=True, last_modified__lt=deltat)
    logging.info("Stale flagged: %d" % fjobs.count())

    skey = {'CREATED' : 'fcr',
            'RUNNING' : 'frn',
            'EXITING' : 'fex',
            }
################

    for j in cjobs:
        # flag stale created jobs
        if j.flag: continue
        msg = "In CREATED state >%dhrs so flagging the job" % ctimeout 
        m = Message(job=j, msg=msg, client="127.0.0.1")
        m.save()
#        db.jobs.update({'name': j.id},{ '$push' : { 'msgs' : msg} }, upsert=True)
        j.flag = True
        j.save()

    for j in rjobs:
        # flag stale running jobs
        if j.flag: continue
        msg = "In RUNNING state >%dhrs so flagging the job" % rtimeout 
        m = Message(job=j, msg=msg, client="127.0.0.1")
        m.save()
#        db.jobs.update({'name': j.id},{ '$push' : { 'msgs' : msg} }, upsert=True)
        j.flag = True
        j.save()

    for j in fjobs:
        # move flagged jobs to FAULT state
        msg = "%s -> FAULT because job been flagged for >%dhrs" % (j.state, ftimeout)
        m = Message(job=j, msg=msg, client="127.0.0.1")
        m.save()
#        db.jobs.update({'name': j.id},{ '$push' : { 'msgs' : msg} }, upsert=True)
        msg = "%s_%s: %s -> FAULT, stale job" % (j.fid.name, j.cid, j.state)
        logging.debug(msg)
        j.state = fstate
        j.save()

################

#        prefix = skey[statenow.name]
#        key = "%s%d" % (prefix, j.fid.id)
#        try:
#            val = cache.decr(key)
#        except ValueError:
#            # key not known so set to current count
#            msg = "MISS key: %s" % key
#            logging.debug(msg)
#            val = Job.objects.filter(fid=j.fid, state=statenow).count()
#            added = cache.add(key, val)
#            if added:
#                msg = "Added DB count for key %s : %d" % (key, val)
#                logging.debug(msg)
#            else:
#                msg = "Failed to decr key: %s" % key
#                logging.debug(msg)
#
#        key = "fft%d" % j.fid.id
#        try:
#            val = cache.incr(key)
#        except ValueError:
#            # key not known so set to current count
#            msg = "MISS key: %s" % key
#            logging.debug(msg)
#            val = Job.objects.filter(fid=j.fid, state=fstate).count()
#            added = cache.add(key, val)
#            if added:
#                msg = "Added DB count for key %s : %d" % (key, val)
#                logging.debug(msg)
#            else:
#                msg = "Failed to incr key: %s" % key
#                logging.debug(msg)


    for j in ejobs:
        # move EXITING jobs to DONE state
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
#    connection = Connection('py-stor', 27017)
#    db = connection.jobdb
    c = statsd.StatsClient(host='py-heimdallr', port=8125)
    stat = 'apfmon.monexpire'
    start = time()
    rc = main()
    elapsed = time() - start
    c.timing(stat,int(elapsed))
    sys.exit(rc)
