from datetime import timedelta, datetime
import logging
from optparse import OptionParser
import pytz
import statsd
import sys
from time import time

sys.path.append('/var/local/django')

from atl.mon.models import Job
from django.conf import settings
from django.core.cache import cache

"""
Remove jobs from DB which have been in DONE/FAULT state for
a set number of hours
"""

def main(c):
    parser = OptionParser(usage='''%prog [OPTIONS]
Delete job records which have been in a final state longer
than the specified number of hours
''')
    parser.add_option("-t",
                       dest="t",
                       default=24,
                       action="store",
                       type="int",
                       help="Set number of hours for cleaning threshold [default 24]")
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
    
    dt = datetime.now(pytz.utc) - timedelta(hours=options.t)
    djobs = Job.objects.filter(state__name='DONE', last_modified__lt=dt)
    fjobs = Job.objects.filter(state__name='FAULT', last_modified__lt=dt)
    
    msg = 'DONE: %d' % djobs.count()
    logging.info(msg)
    msg = 'FAULT: %d' % fjobs.count()
    logging.info(msg)
    c.gauge('apfmon.dclean',djobs.count())
    c.gauge('apfmon.fclean',fjobs.count())
    djobs.delete()
    fjobs.delete()

# commented with suspicion of slow query

#    for j in djobs:
#        key = "fdn%d" % j.fid.id
#        try:
#            val = cache.decr(key)
#        except ValueError:
#            # key not known so set to current count
#            msg = "MISS key: %s" % key
#            print msg 
#            val = Job.objects.filter(fid=j.fid, state=j.state).count()
#            added = cache.add(key, val)
#            if added:
#                msg = "Added DB count for key %s : %d" % (key, val)
#                print msg 
#            else:
#                msg = "Failed to decr key: %s" % key
#                print msg 
#    
#    #    if j.fid != 35:
#    #        j.delete()
#        print j
#        j.delete()

#    for j in fjobs:
#        key = "fft%d" % j.fid.id
#        try:
#            val = cache.decr(key)
#        except ValueError:
#            msg = "MISS key: %s" % key
#            print msg 
#            # key not known so set to current count
#            val = Job.objects.filter(fid=j.fid, state=j.state).count()
#            added = cache.add(key, val)
#            if added:
#                msg = "Added DB count for key %s : %d" % (key, val)
#                print msg 
#            else:
#                msg = "Failed to decr key: %s" % key
#                print msg 
#    
#    #    if j.fid != 35:
#        j.delete()
#    
#    print 'DONE:',djobs.count()
#    print 'FAULT:',fjobs.count()

if __name__ == "__main__":
    c = statsd.StatsClient(settings.GRAPHITE['host'],
                           settings.GRAPHITE['port'])
    stat = 'apfmon.monclean'
    start = time()
    rc = main(c)
    elapsed = time() - start
    c.timing(stat,int(elapsed))
    msg = "mon-clean.py elapsed time: %d" % int(elapsed)
    logging.info(msg)
    sys.exit(rc)
