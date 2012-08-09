import sys

sys.path.append('/var/local/django')

from atl.mon.models import Job
from datetime import timedelta, datetime
from django.core.cache import cache

# clean pyf Job
dt = datetime.now() - timedelta(hours=12)
djobs = Job.objects.filter(state__name='DONE', last_modified__lt=dt)
fjobs = Job.objects.filter(state__name='FAULT', last_modified__lt=dt)

for j in djobs:
    key = "fdn%d" % j.fid.id
    val = cache.decr(key)
    if val is None:
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

    if j.fid != 35:
        j.delete()

for j in fjobs:
    key = "fft%d" % j.fid.id
    val = cache.decr(key)
    if val is None:
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

    if j.fid != 35:
        j.delete()
