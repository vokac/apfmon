import pytz
import statsd
import sys
from time import time

sys.path.append('/var/local/django')

from atl.mon.models import Job
from datetime import timedelta, datetime
from django.core.cache import cache

"""
Remove jobs from DB which have been in DONE/FAULT state for 24hrs
"""

def main():
    # clean pyf Job
    dt = datetime.now(pytz.utc) - timedelta(hours=30)
    djobs = Job.objects.filter(state__name='DONE', last_modified__lt=dt)
    fjobs = Job.objects.filter(state__name='FAULT', last_modified__lt=dt)
    
    print 'DONE:',djobs.count()
    print 'FAULT:',fjobs.count()
    for j in djobs:
        key = "fdn%d" % j.fid.id
        try:
            val = cache.decr(key)
        except ValueError:
            # key not known so set to current count
            msg = "MISS key: %s" % key
            print msg 
            val = Job.objects.filter(fid=j.fid, state=j.state).count()
            added = cache.add(key, val)
            if added:
                msg = "Added DB count for key %s : %d" % (key, val)
                print msg 
            else:
                msg = "Failed to decr key: %s" % key
                print msg 
    
    #    if j.fid != 35:
    #        j.delete()
        print j
        j.delete()
    
    for j in fjobs:
        key = "fft%d" % j.fid.id
        try:
            val = cache.decr(key)
        except ValueError:
            msg = "MISS key: %s" % key
            print msg 
            # key not known so set to current count
            val = Job.objects.filter(fid=j.fid, state=j.state).count()
            added = cache.add(key, val)
            if added:
                msg = "Added DB count for key %s : %d" % (key, val)
                print msg 
            else:
                msg = "Failed to decr key: %s" % key
                print msg 
    
    #    if j.fid != 35:
        j.delete()
    
    print 'DONE:',djobs.count()
    print 'FAULT:',fjobs.count()

if __name__ == "__main__":
    c = statsd.StatsClient(host='py-heimdallr', port=8125)
    stat = 'apfmon.monclean'
    start = time()
    rc = main()
    elapsed = time() - start
    c.timing(stat,int(elapsed))
    sys.exit(rc)
