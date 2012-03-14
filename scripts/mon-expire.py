from datetime import timedelta, datetime
import logging
from optparse import OptionParser
import sys

sys.path.append('/var/local/django')

from atl.mon.models import Job
from atl.mon.models import Message
from atl.mon.models import State
#from atl.mon.models import Factory


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
    
    deltat = datetime.now() - timedelta(hours=18)
    cjobs = Job.objects.filter(state=cstate, last_modified__lt=deltat)
    logging.info("created: %d" % cjobs.count())
    
    deltat = datetime.now() - timedelta(hours=48)
    rjobs = Job.objects.filter(state=rstate, last_modified__lt=deltat)
    logging.info("running: %d" % rjobs.count())
    
    deltat = datetime.now() - timedelta(minutes=30)
    ejobs = Job.objects.filter(state=estate, last_modified__lt=deltat)
    logging.info("exiting: %d" % ejobs.count())
    
    jobs = []
    jobs.extend(cjobs)
    jobs.extend(rjobs)
    for j in jobs:
        msg = "%s -> FAULT, stale job" % j.state
        m = Message(job=j, msg=msg, client="127.0.0.1")
        m.save()
        msg = "%s_%s: %s -> FAULT, stale job" % (j.fid.name, j.cid, j.state)
        logging.debug(msg)
        j.state = fstate
        j.save()

    for j in ejobs:
        msg = "%s -> DONE" % j.state
        m = Message(job=j, msg=msg, client="127.0.0.1")
        m.save()
        msg = "%s_%s: %s -> DONE" % (j.fid.name, j.cid, j.state)
        logging.debug(msg)
        j.state = dstate
        j.save()



if __name__ == "__main__":
    sys.exit(main())
