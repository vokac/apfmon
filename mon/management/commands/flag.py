"""
Retrieve condor log of jobs in created state > timeout
Move to fault/done state based on log content

This method is not scalable and slow to retrieve logs. To be replace by
transient script located at factories.
"""

from django.core.management.base import BaseCommand, CommandError, NoArgsCommand
from apfmon.mon.models import Job
from django.conf import settings
from django.core.cache import cache

import logging
import pytz
import re
import redis
import requests
import socket
import statsd
import sys
import time
from datetime import timedelta, datetime
#from optparse import OptionParser

red = redis.StrictRedis(host=settings.REDIS['host'],
                        port=settings.REDIS['port'], db=0)
stats = statsd.StatsClient(settings.GRAPHITE['host'],
                           settings.GRAPHITE['port'])
expire6hrs = 6*3600
expire2days = 172800
expire5days = 432000
expire7days = 604800

# known CREAM errors
#_MATCH = re.compile('.+CREAM error: (\S+) Error: \S+ Description=\[(.*)\] FaultCause=\[(.*)\] Timestamp', re.DOTALL)
patterns = [
             '(CREAM error: .*)',
             '(CREAM_Delegate Error: .*)',
#             'CREAM_Delegate Error:.*FaultDetail=\[(.*)\]',
             '(Globus error.*)',
             '(globus_ftp_client:.*error.*)',
             '(Job was aborted by the user.*)', 
            ]
_ALL = re.compile('|'.join(p for p in patterns))
_DONE= re.compile('(Job terminated.*)')

class Command(NoArgsCommand):
    args = '<...>'
    help = 'Set state to FAULT for jobs which have errors in their condor log'
    logger = logging.getLogger('apfmon.mon')

    def handle(self, *args, **options):
            ctimeout = 330 # minutes
            start = time.time()
        
            # find job in created state older than ctimeout
            deltat = datetime.now(pytz.utc) - timedelta(minutes=ctimeout)
            # older than now - ctimeout
            cjobs = Job.objects.filter(state='created', created__lt=deltat, flag=False).order_by('-created')
            cnt = cjobs.count()
            msg = 'Number in CREATED state > %d minutes: %d' % (ctimeout, cnt)
            self.stdout.write(msg)
            
            nerr = 0
            ndone = 0
            nmiss = 0
            for j in cjobs:
                url = '/'.join((j.label.fid.url,
                                str(j.created.date()),
                                j.label.name, j.cid+'.log'))

                joburl = '/'.join(('http://apfmon.lancs.ac.uk',
                                   j.label.fid.name,
                                   j.cid))
                                

                try:
                    r = requests.get(url, timeout=1.5)
                except requests.Timeout:
                    msg = 'TIMEOUT: %s' % url
                    self.stdout.write(msg)
                    continue
                except socket.timeout:
                    # this exception is a bug
                    # https://github.com/kennethreitz/requests/issues/1236
                    msg = 'TIMEOUT: %s' % url
                    self.stdout.write(msg)
                    continue
                except:
                    msg = 'EXCEPTION: %s' % url
                    self.stdout.write(msg)
                    

                errmatch = _ALL.findall(r.text)
                donematch = _DONE.findall(r.text)
                if errmatch:
                    nerr += 1
                    msg = 'ERROR: %s' % joburl
#                    self.stdout.write(msg)

                    msg = "Error seen (see stdlog) setting state %s -> fault" % j.state
                    element = "%f %s %s" % (time.time(), '127.0.0.1', msg)
                    key = ':'.join(('joblog',j.jid))
                    red.rpush(key, element)
                    red.expire(key, expire6hrs)
#                    j.flag = True
                    j.state = 'fault'
                    j.save()
                    for errs in errmatch:
                        for err in errs:
                            if not err: continue
                            msg = 'MSG: %s' % err
#                            self.logger.debug(msg)
                            msg = err[:140]
                            element = "%f %s %s" % (time.time(), '127.0.0.1', msg)
                            red.rpush(key, element)

                    # add jobid to the fault set
                    key = ':'.join(('fault',j.label.fid.name,j.label.name))
                    red.sadd(key,j.jid)
                    red.expire(key,expire7days)
                elif donematch:
                    ndone += 1
                    msg = 'DONE: %s' % joburl
#                    self.stdout.write(msg)

                    msg = "Job terminated without error (see stdlog) setting state %s -> done" % j.state
                    element = "%f %s %s" % (time.time(), '127.0.0.1', msg)
                    key = ':'.join(('joblog',j.jid))
                    red.rpush(key, element)
                    red.expire(key, expire6hrs)
                    j.state = 'done'
                    j.save()
                    for dns in donematch:
                        for dn in dns:
                            if not dn: continue
                            msg = dn[:140]
                            element = "%f %s %s" % (time.time(), '127.0.0.1', msg)
                            red.rpush(key, element)

                    # add jobid to the done set
                    key = ':'.join(('done',j.label.fid.name,j.label.name))
                    red.sadd(key,j.jid)
                    red.expire(key,expire7days)
                else:
                    msg = 'MISS: %s' % url
#                    self.stdout.write(msg)
                    nmiss += 1
        
            msg = 'error:%d done:%d miss:%d' % (nerr, ndone, nmiss)
            self.stdout.write(msg)
            msg = 'Number in CREATED state > %d minutes: %d' % (ctimeout, cnt)
            self.stdout.write(msg)
            elapsed = time.time() - start
            stats.gauge('apfmon.flagged', cnt)
