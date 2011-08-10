import sys

sys.path.append('/var/local/django')

from atl.mon.models import Job
from datetime import timedelta, datetime

# clean pyf Job
dt = datetime.now() - timedelta(hours=24)
jobs = Job.objects.filter(last_modified__lt=dt)
if jobs.count():
  print jobs.count()
#if jobs: print jobs[0]
  jobs.delete()
