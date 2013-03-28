from apfmon.mon.models import Factory
from apfmon.mon.models import Job
from apfmon.mon.models import Label

from apfmon.kit.models import Site
from apfmon.kit.models import BatchQueue
from apfmon.kit.models import WMSQueue

import csv
import logging
import pytz
import re
import redis
import statsd
import string
import sys
import time
from operator import itemgetter
from datetime import timedelta, datetime
from django.shortcuts import redirect, render_to_response, get_object_or_404
from django.db.models import Count
from django.db.models import Q
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.http import HttpResponseRedirect
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.conf import settings
from django.core.context_processors import csrf
from django.core.mail import mail_managers
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.serializers.json import DjangoJSONEncoder
from django.core.urlresolvers import reverse
from django.core.exceptions import MultipleObjectsReturned

try:
    import json as json
except ImportError, err:
    logging.error('Cannot import json, using simplejson')
    import simplejson as json

ELOGREGEX = re.compile('(.*elog[^0-9]*)([0-9]+)', re.IGNORECASE)
SAVANNAHREGEX = re.compile('(.*savannah[^0-9]*)([0-9]+)', re.IGNORECASE)
GGUSREGEX = re.compile('(.*ggus[^0-9]*)([0-9]+)', re.IGNORECASE)
ELOGURL = 'https://atlas-logbook.cern.ch/elog/ATLAS+Computer+Operations+Logbook/%s'
GGUSURL = 'https://ggus.eu/ws/ticket_info.php?ticket=%s'
SAVANNAHURL = 'https://savannah.cern.ch/support/?%s'

ss = statsd.StatsClient(settings.GRAPHITE['host'], settings.GRAPHITE['port'])
red = redis.StrictRedis(settings.REDIS['host'] , port=settings.REDIS['port'], db=0)

# Flows
# 1. CREATED <- condor_id (Entry)
# 3. RUNNING <- signal from pilot-wrapper
# 4. EXITING <- signal from pilot-wrapper
# 5. DONE <- signal from cronjob script (mon-expire.py) jobstate=4

def jobs1(request, lid, state, p=1):
    """
    Rendered view of a set of Jobs for particular Label and optional state
    """

    lab = get_object_or_404(Label, id=int(lid))

    jobs = Job.objects.filter(label=lab,state=state)
    jobs = jobs.order_by('-last_modified')
    pages = Paginator(jobs, 100)

    try:
        page = pages.page(p)
    except (EmptyPage, InvalidPage):
        page = pages.page(pages.num_pages)

    context = {
                'label' : lab,
                'name' : lab.name,
                'factoryname' : lab.fid.name,
                'fid' : lab.fid.id,
                'pandaq' : lab.batchqueue,
                'statename' : state,
                'jobs' : jobs,
                'pages' : pages,
                'page' : page,
                }

    return render_to_response('mon/jobs.html', context)


def job1(request, fid, cid):
    """
    Rendered view of job information
    """

    # handle both Factory id and name
    try:
        id = int(fid)
        f = get_object_or_404(Factory, id=id)
    except ValueError:
        f = get_object_or_404(Factory, name=fid)
        
    jid = ':'.join((f.name,cid))
    job = get_object_or_404(Job, jid=jid)

    msglist = red.lrange(job.jid, 0, -1)

    msgs = []
    for msg in msglist:
        # msg is a string with format:
        # "<epoch_time> <client_ip> <some message with spaces>"
        (t, ip, txt) = msg.split(' ',2)
        msg = {'received' : datetime.fromtimestamp(float(t)),
               'client'   : ip,
               'msg'      : txt, 
             }
 
        msgs.append(msg)

    date = ''
    if f.factory_type != 'glideinWMS':
        date = "%d-%02d-%02d" % (job.created.year, job.created.month, job.created.day)
    # these need to come from Factory info
    out = "%s/%s/%s/%s.out"
    err = "%s/%s/%s/%s.err"
    log = "%s/%s/%s/%s.log"

    dir = str(job.label).translate(string.maketrans('/:','__'))

    outurl = out % (f.url, date, dir, job.cid)
    errurl = err % (f.url, date, dir, job.cid)
    logurl = log % (f.url, date, dir, job.cid)

    
    # datetime.fromtimestamp(time.time())
    context = {
                'outurl'  : outurl,
                'errurl'  : errurl,
                'logurl'  : logurl,
                'factory' : f,
                'job'     : job,
                'msgs'    : msgs,
#                'pids' : pids,
                }

    return render_to_response('mon/job.html', context)

def history(request, qid):
    """
    Rendered view of historic graphs
    """

#    try:
#        queue = Queue.objects.get(id=qid)
#    except Queue.DoesNotExist:
#        queue = None

    context = {
#                'q' : queue,
#                'qid' : qid,
            }

    return render_to_response('mon/history.html', context)

def debug(request):
    """
    Rendered view of selected Jobs
    """

    dt = datetime.now(pytz.utc) - timedelta(minutes=60)
    fault = Job.objects.filter(last_modified__gt=dt, state__name='FAULT')
    done = Job.objects.filter(last_modified__gt=dt, state__name='DONE').filter(result=0)
    flagged = Job.objects.filter(last_modified__gt=dt, flag=True)
    havejob = done.filter(result=0)

    dt = datetime.now(pytz.utc) - timedelta(hours=96)
    ancient = Job.objects.filter(created__lt=dt).order_by('created').exclude(state__name__in=['FAULT','DONE'])

    context = {
                'ancient' : ancient,
                'flagged' : flagged,
                'fault' : fault,
                'done' : done,
                'havejob' : havejob,
                }

    return render_to_response('mon/debug.html', context)

#@cache_page(60 * 10)
def factory(request, fid):
    """
    Rendered view of Factory instance. Lists all factory labels with
    a count of jobs in each state.
    """

    try:
        id = int(fid)
    except ValueError:
        raise Http404

    f = get_object_or_404(Factory, id=id)
    pandaqs = BatchQueue.objects.all()
    labels = Label.objects.filter(fid=f)
    jobs = Job.objects.filter(label__fid=f)
    dt = datetime.now(pytz.utc) - timedelta(hours=1)
    dtlab = datetime.now(pytz.utc) - timedelta(weeks=3)

    lifetime = 300
    rows = []
    for lab in labels:
        if lab.last_modified < dtlab:
            # todo: mark label inactive lab.save()
            continue
        ncreated = 0
        nsubmitted = 0
        nrunning = 0
        nexiting = 0
        ndone = 0
        nfault = 0

        key = "lcr%d" % lab.id
        val = cache.get(key)
        if val is None:
            msg = "MISS key: %s" % key
            logging.debug(msg)
            # key not known so set to current count
            val = jobs.filter(label=lab, state='created').count()
            added = cache.add(key, val, lifetime)
            if added:
                msg = "Added DB count for key %s : %d" % (key, val)
                logging.warn(msg)
            else:
                msg = "Failed to add DB count for key %s : %d" % (key, val)
                logging.warn(msg)
        ncreated = val

        key = "lrn%d" % lab.id
        val = cache.get(key)
        if val is None:
            msg = "MISS key: %s" % key
            logging.debug(msg)
            # key not known so set to current count
            val = jobs.filter(label=lab, state='running').count()
            added = cache.add(key, val, lifetime)
            if added:
                msg = "Added DB count for key %s : %d" % (key, val)
                logging.warn(msg)
            else:
                msg = "Failed to add DB count for key %s : %d" % (key, val)
                logging.warn(msg)
        nrunning = val

        key = "lex%d" % lab.id
        val = cache.get(key)
        if val is None:
            msg = "MISS key: %s" % key
            logging.debug(msg)
            # key not known so set to current count
            val = jobs.filter(label=lab, state='exiting').count()
            added = cache.add(key, val, lifetime)
            if added:
                msg = "Added DB count for key %s : %d" % (key, val)
                logging.warn(msg)
            else:
                msg = "Failed to add DB count for key %s : %d" % (key, val)
                logging.warn(msg)
        nexiting = val

        key = "ldn%d" % lab.id
        val = cache.get(key)
        if val is None:
            msg = "MISS key: %s" % key
            logging.debug(msg)
            # key not known so set to current count
            val = jobs.filter(label=lab, state='done').count()
            added = cache.add(key, val, lifetime)
            if added:
                msg = "Added DB count for key %s : %d" % (key, val)
                logging.warn(msg)
            else:
                msg = "Failed to add DB count for key %s : %d" % (key, val)
                logging.warn(msg)
        ndone = val

        statcr = 'pass'
        if ncreated >= 500:
            statcr = 'warn'

        statdone = 'pass'
        if ndone <= 0:
            statdone = 'warn'

        statfault = 'pass'
        if nfault >= 50:
            statfault = 'hot'

        delayed = datetime.now(pytz.utc) - timedelta(minutes=5)
        stale = datetime.now(pytz.utc) - timedelta(minutes=30)
        activity = 'ok'
        if delayed > lab.last_modified:
            activity = 'warn'
        if stale > lab.last_modified:
            activity = 'stale'
    
        row = {
            'label' : lab,
            'pandaq' : lab.batchqueue,
#            'graph' : url % q.id,
            'ncreated' : ncreated,
            'nrunning' : nrunning,
            'nexiting' : nexiting,
            'ndone' : ndone,
            'nfault' : nfault,
            'statcr' : statcr,
            'statdone' : statdone,
            'statfault' : statfault,
            'activity' : activity,
            }

        rows.append(row)

    context = {
            'rows' : rows,
            'jobs' : jobs,
            'pandaqs' : pandaqs,
            'factory' : f,
            }

    return render_to_response('mon/factory.html', context)

def pandaq(request, qid, p=1):
    """
    Rendered view of panda queue for all factories
    """

    q = get_object_or_404(BatchQueue, id=qid)

    labels = Label.objects.filter(batchqueue=q)
    dt = datetime.now(pytz.utc) - timedelta(hours=1)
    dtdead = datetime.now(pytz.utc) - timedelta(days=10)
    # factories with labels serving selected batchqueue
    fs = Factory.objects.filter(label__in=labels)

    rows = []
    for lab in labels:
        if lab.last_modified < dtdead: continue
        row = {}
        ncreated = 0
        nsubmitted = 0
        nrunning = 0
        nexiting = 0
        ndone = 0
        nfault = 0
        jobs = Job.objects.filter(label=lab)
        ncreated = jobs.filter(state='created').count()
        nrunning = jobs.filter(state='running').count()
        nexiting = jobs.filter(state='exiting').count()
#        ndone = jobs.filter(state='done', last_modified__gt=dt).count()
        ndone = jobs.filter(state='done').count()
#        nfault = jobs.filter(state='fault', last_modified__gt=dt).count()
        nfault = jobs.filter(state='fault').count()
#        nmiss = jobs.filter(state='done', last_modified__gt=dt, result=20).count()
        nmiss = jobs.filter(state='done', result=20).count()
    
        row['jobcount'] = {
                'created' : ncreated,
                'running' : nrunning,
                'exiting' : nexiting,
                'done' : ndone,
                'fault' : nfault,
                'miss' : nmiss,
                }

        row['label'] = lab
    
        statdone = 'pass'
        if nexiting == 0:
            statdone = 'fail'
        elif nexiting <= 5:
            statdone = 'warn'
    
        statfault = 'hot'
#        if nfault <= 5:
#            statfault = 'warn'
        if nfault == 0:
            statfault = 'pass'

        row['statdone'] = statdone
        row['statfault'] = statfault

        dtwarn = datetime.now(pytz.utc) - timedelta(minutes=5)
        dtstale = datetime.now(pytz.utc) - timedelta(minutes=10)

        active = 'stale'
        if lab.last_modified > dtstale:
            active = 'warn'
        if lab.last_modified > dtwarn:
            active = 'pass'

        row['activity'] = active

        rows.append(row)

    pages = Paginator(Job.objects.filter(label__batchqueue=qid).order_by('-last_modified'), 100)
    jobs = Job.objects.filter(label__batchqueue=qid).order_by('-last_modified')[:100]

    context = {
            'pandaq' : q,
            'rows' : rows,
            'jobs' : jobs,
            'pages' : pages,
            'page' : pages.page(p),
            }

    return render_to_response('mon/pandaq.html', context)

def oldindex(request):
    """
    Rendered view of front mon page
    """

    factories = Factory.objects.all()
   
    dt = datetime.now(pytz.utc) - timedelta(hours=1)
    jobs = Job.objects.all()

    rows = []
    for f in factories:
        ncreated = 0
        nrunning = 0
        nexiting = 0
        ndone = 0
        nfault = 0
        ntotal = jobs.count()
        ncreated = jobs.filter(fid=f, state='created').count()
        nrunning = jobs.filter(fid=f, state='running').count()
        nexiting = jobs.filter(fid=f, state='exiting').count()
        ndone = jobs.filter(fid=f, state='done', last_modified__gt=dt).count()
        nfault = jobs.filter(fid=f, state='fault', last_modified__gt=dt).count()
        statdone = 'pass'
        if nexiting == 0:
            statdone = 'fail'
        elif nexiting <= 5:
            statdone = 'warn'
        row = {
            'factory' : f,
            'ncreated' : ncreated,
            'nrunning' : nrunning,
            'nexiting' : nexiting,
            'ndone' : ndone,
            'nfault' : nfault,
            'statdone' : statdone,
            }

        rows.append(row)

    context = {
            'rows' : rows,
            'plot' : 'off',
            }

    return render_to_response('mon/total.html', context)

def offline(request):

    context = {}
    return render_to_response('mon/offline.html', context)

def count(request, state=None, fid=None, qid=None):
    """
    return count of Jobs
    """

    if not (fid and qid and state):
        content = "Bad request"
        return HttpResponseBadRequest(content, mimetype="text/plain")

    f = None
    try:
        f = Factory.objects.get(id=fid)
    except Factory.DoesNotExist:
        if fid != '0':
            msg = "Factory %s not found when counting" % fid
            logging.debug(msg)
            content = "Bad request"
            return HttpResponseBadRequest(content, mimetype="text/plain")

    q = None
    if qid:
        try:
            q = BatchQueue.objects.get(id=qid)
        except BatchQueue.DoesNotExist:
            if qid != '0':
                msg = "Queue %s not found when counting" % qid
                logging.debug(msg)
                content = "Bad request"
                return HttpResponseBadRequest(content, mimetype="text/plain")
        
    s = None
    if state:
        try:
            s = State.objects.get(name=state)
        except State.DoesNotExist:
            msg = "State %s not found when counting" % state
            logging.debug(msg)
            content = "Bad request"
            return HttpResponseBadRequest(content, mimetype="text/plain")

    if f:
        if q and s:
            jobs = Job.objects.filter(fid=f, state=s, label__batchqueue=q)
        elif s:
            jobs = Job.objects.filter(fid=f, state=s)
        elif q:
            jobs = Job.objects.filter(fid=f, label__batchqueue=q)
        else:
            jobs = Job.objects.filter(fid=f)
    else:
        if q and s:
            jobs = Job.objects.filter(state=s, label__batchqueue=q)
        elif s:
            jobs = Job.objects.filter(state=s)
        elif q:
            jobs = Job.objects.filter(label__batchqueue=q)
        else:
            jobs = Job.objects.all()


    if state in ['FAULT', 'DONE']:
        deltat = datetime.now(pytz.utc) - timedelta(hours=1)
        jobs = jobs.filter(last_modified__gt=deltat)

    result = jobs.count()

    return HttpResponse("%s" % result, mimetype="text/plain")

def st(request):
    """
    Unrendered handle reported state of condor job, via mon-expire.py cron

    JobStatus in job ClassAds
    0   Unexpanded  U
    1   Idle    I
    2   Running     R
    3   Removed     X
    4   Completed   C
    5   Held    H
    6   Submission_err  E

    Condor globusstate:
    1   PENDING The job is waiting for resources to become available to run.
    2   ACTIVE  The job has received resources and the application is executing.
    4   FAILED  The job terminated before completion because an error, user-triggered cancel, or system-triggered cancel.
    8   DONE    The job completed successfully
    16  SUSPENDED   The job has been suspended. Resources which were allocated for this job may have been released due to some scheduler-specific reason.
    32  UNSUBMITTED The job has not been submitted to the scheduler yet, pending the reception of the GLOBUS_GRAM_PROTOCOL_JOB_SIGNAL_COMMIT_REQUEST signal from a client.
    64  STAGE_IN    The job manager is staging in files to run the job.
    128 STAGE_OUT   The job manager is staging out files generated by the job.
    0xFFFFF     ALL     A mask of all job states.

    """
    fid = request.POST.get('fid', None)
    cid = request.POST.get('cid', None)
    js = request.POST.get('js', None)
    gs = request.POST.get('gs', None)

    if not cid:
        content = "Bad request"
        return HttpResponseBadRequest(content, mimetype="text/plain")

    try:
        j = Job.objects.get(fid__name=fid, cid=cid)
    except Job.DoesNotExist:
        content = "DoesNotExist: %s" % cid
        return HttpResponseBadRequest(content, mimetype="text/plain")

    msg = None

    if j.state.name in ['DONE', 'FAULT']:
        msg = "Terminal: %s, no state change allowed. js=%s, gs=%s" % (j.cid, js, gs)
        j.flag = True
        j.save()

    if j.state.name in ['EXITING']:
        if js in ['4']:
            # EXITING job finished OK (js=4)
            msg = "%s -> DONE: %s (COMPLETED) js=%s, gs=%s" % (j.state, j.cid, js, gs)
            j.state = State.objects.get(name='DONE')
            j.save()
        elif js in ['1', '2']:
            # EXITING job finished but condor not uptodate (js=1)
            msg = "%s -> DONE: (PENDING) %s js=%s, gs=%s" % (j.state, j.cid, js, gs)
            j.state = State.objects.get(name='DONE')
            j.save()
        else:
            # EXITING job in bad state, set FAULT
            msg = "Bad state %s: %s js=%s, gs=%s" % (j.state, j.cid, js, gs)
            j.state = State.objects.get(name='FAULT')
            j.save()

    if msg:
        element = "%f %s %s" % (time.time(), request.META['REMOTE_ADDR'], msg)
        red.rpush(j.jid, element)
    else:
        msg = "HANDLE-THIS %s: Current:%s, js=%s, gs=%s" % (j.cid, j.state, js, gs)
        j.flag = True
        j.save()
        logging.warn(msg)

    return HttpResponse("OK", mimetype="text/plain")

def stale(request):
    """
    Handle job which has been too long in a particular state
    Called by the mon-stale.py cronjob using jobs given by old() func
    """

    jdecode = json.JSONDecoder()

    raw = request.POST.get('data', None)
    fid = request.POST.get('fid', None)

    if not (fid and raw):
        content = "Bad request"
        return HttpResponseBadRequest(content, mimetype="text/plain")

    try:
        data = jdecode.decode(raw)
        msg = "JSON stale length: %d" % len(data)
        logging.debug(msg)
    except:
        msg = "Error decoding POST json data"
        logging.error(msg)
        content = "Bad request"
        return HttpResponseBadRequest(content, mimetype="text/plain")

    for d in data:
        if not d: continue
        cid = d['cid']
        js = d['jobstate']
        gs = d.get('globusstate', None)

        if not (fid and cid and js):
            content = "Bad request"
            return HttpResponseBadRequest(content, mimetype="text/plain")

        try:
            j = Job.objects.get(fid__name=fid, cid=cid)
        except Job.DoesNotExist:
            content = "DoesNotExist: %s_%s" % (fid, cid)
            return HttpResponseBadRequest(content, mimetype="text/plain")

        msg = None
    
        if j.state.name in ['CREATED']:
            if js in ['4']:
                # CREATED job is done according to condor therefore missed state change
                msg = "Missed state change. Current:%s, js=%s, gs=%s" % (j.state, js, gs)
                j.state = State.objects.get(name='DONE')
                j.flag = True
                j.save()
            elif js in ['2']:
                # CREATED job is running according to condor therefore missed state change
                msg = "Missed state change. Current:%s, js=%s, gs=%s" % (j.state, js, gs)
                j.flag = True
                j.save()
            else:
                # CREATED job in bad state, set FAULT
                msg = "Stale %s -> FAULT js=%s, gs=%s" % (j.state, js, gs)
                j.state = State.objects.get(name='FAULT')
                j.save()
    
        elif j.state.name in ['RUNNING']:
            if js in ['4']:
                # RUNNING job taking too long
                msg = "Missed state change. Current:%s, js=%s, gs=%s" % (j.state, js, gs)
                j.state = State.objects.get(name='DONE')
                j.flag = True
                j.save()
            else:
                msg = "Stale %s -> FAULT js=%s, gs=%s" % (j.state, js, gs)
                j.state = State.objects.get(name='FAULT')
                j.save()
    
        elif j.state.name in ['EXITING']:
            msg = "Stale %s (slow middleware), js=%s, gs=%s" % (j.state, js, gs)
            j.save()
    
        elif j.state.name in ['DONE', 'FAULT']:
            msg = "Stale? Terminal state. Current:%s, js=%s, gs=%s" % (j.state, js, gs)
            j.flag = True
            j.save()
    
        else:
            msg = "Stale flagged Current:%s, js=%s, gs=%s" % (j.state, js, gs)
            j.flag = True
            j.save()
    
        if msg:
            element = "%f %s %s" % (time.time(), request.META['REMOTE_ADDR'], msg)
            red.rpush(j.jid, element)

    return HttpResponse("OK", mimetype="text/plain")

def rn(request, fid, cid):
    """
    Handle 'rn' signal from a running job
    """
    stat = 'apfmon.rn'
    start = time.time()

    try:
        f = Factory.objects.get(name=fid)
    except Factory.DoesNotExist:
        msg = "Factory %s not found" % fid
        logging.debug(msg)
        content = "Bad request"
        return HttpResponseBadRequest(content, mimetype="text/plain")

    try:
        j = Job.objects.get(cid=cid, label__fid=f)
    except Job.DoesNotExist, e:
        msg = "RN unknown job: %s_%s" % (f, cid)
#PAL - pending fix for apfv2        logging.warn(msg)
        content = "Fine"
        return HttpResponseBadRequest(content, mimetype="text/plain")

    msg = None

    if j.state == 'created':
        msg = "%s -> RUNNING" % j.state
        element = "%f %s %s" % (time.time(), request.META['REMOTE_ADDR'], msg)
        red.rpush(j.jid, element)

        j.state = 'running'
        if j.flag:
            j.flag = False
            msg = "RUNNING now, flag cleared"
            element = "%f %s %s" % (time.time(), request.META['REMOTE_ADDR'], msg)
            red.rpush(j.jid, element)
        j.save()

#        key = "fcr%d" % f.id
#        try:
#            val = cache.decr(key)
#        except ValueError:
#            # key not known so set to current count
#            msg = "MISS key: %s" % key
#            logging.debug(msg)
#            val = Job.objects.filter(fid=f, state__name='CREATED').count()
#            added = cache.add(key, val)
#            if added:
#                msg = "Added DB count for key %s : %d" % (key, val)
#                logging.warn(msg)
#            else:
#                msg = "Failed to decr key: %s" % key
#                logging.warn(msg)
#
#        key = "frn%d" % f.id
#        try:
#            val = cache.incr(key)
#        except ValueError:
#            # key not known so set to current count
#            msg = "MISS key: %s" % key
#            logging.debug(msg)
#            val = Job.objects.filter(fid=f, state__name='RUNNING').count()
#            added = cache.add(key, val)
#            if added:
#                msg = "Added DB count for key %s : %d" % (key, val)
#                logging.debug(msg)
#            else:
#                msg = "Failed to incr key: %s" % key
#                logging.warn(msg)
#
#        key = "lcr%d" % j.label.id
#        try:
#            val = cache.decr(key)
#        except ValueError:
#            msg = "MISS key: %s" % key
#            logging.debug(msg)
#            # key not known so set to current count
#            val = Job.objects.filter(label=j.label, state__name='CREATED').count()
#            added = cache.add(key, val)
#            if added:
#                msg = "Added DB count for key %s : %d" % (key, val)
#                logging.debug(msg)
#            else:
#                msg = "Failed to decr key: %s" % key
#                logging.warn(msg)
#
#        key = "lrn%d" % j.label.id
#        try:
#            val = cache.incr(key)
#        except ValueError:
#            msg = "MISS key: %s" % key
#            logging.debug(msg)
#            # key not known so set to current count
#            val = Job.objects.filter(label=j.label, state__name='RUNNING').count()
#            added = cache.add(key, val)
#            if added:
#                msg = "Added DB count for key %s : %d" % (key, val)
#                logging.debug(msg)
#            else:
#                msg = "Failed to incr key: %s" % key
#                logging.warn(msg)

    else:
        msg = "%s -> RUNNING (WARN: state not CREATED)" % j.state
        element = "%f %s %s" % (time.time(), request.META['REMOTE_ADDR'], msg)
        red.rpush(j.jid, element)

        j.state = 'running'
        j.flag = True
        j.save()

    elapsed = time.time() - start
    ss.timing(stat,int(elapsed))
    return HttpResponse("OK", mimetype="text/plain")

def ex(request, fid, cid, sc=None):
    """
    Handle 'ex' signal from exiting wrapper
    """
    stat = 'apfmon.ex'
    start = time.time()
    
    try:
        f = Factory.objects.get(name=fid)
    except Factory.DoesNotExist:
        msg = "Factory %s not found" % fid
        logging.debug(msg)
        content = "Bad request"
        return HttpResponseBadRequest(content, mimetype="text/plain")

    jid = ':'.join((fid,cid))
    try:
        j = Job.objects.get(jid=jid)
    except Job.DoesNotExist, e:
        msg = "EX unknown Job: %s:%s" % (f, cid)
#PAL - pending fix for apfv2        logging.warn(msg)
        return HttpResponseBadRequest('Fine', mimetype="text/plain")
    
    msg = None

    if j.state in ['done', 'fault']:
        msg = "Terminal: %s, no state change allowed." % j.state
        element = "%f %s %s" % (time.time(), request.META['REMOTE_ADDR'], msg)
        red.rpush(j.jid, element)

        j.flag = True
        j.save()

    elif j.state == 'running':
        msg = "%s -> EXITING statuscode: %s" % (j.state, sc)
        element = "%f %s %s" % (time.time(), request.META['REMOTE_ADDR'], msg)
        red.rpush(j.jid, element)

        j.state = 'exiting'
        if sc:
            j.result = (sc)
        else:
            j.flag = True
        j.save()

#        key = "fex%d" % f.id
#        try:
#            val = cache.incr(key)
#        except ValueError:
#            msg = "MISS key: %s" % key
#            logging.debug(msg)
#            # key not known so set to current count
#            val = Job.objects.filter(fid=f, state__name='EXITING').count()
#            added = cache.add(key, val)
#            if added:
#                msg = "Added DB count for key %s : %d" % (key, val)
#                logging.debug(msg)
#            else:
#                msg = "Failed to incr key: %s" % key
#                logging.warn(msg)
#
#        key = "frn%d" % f.id
#        try:
#            val = cache.decr(key)
#        except ValueError:
#            msg = "MISS key: %s" % key
#            logging.debug(msg)
#            # key not known so set to current count
#            val = Job.objects.filter(fid=f, state__name='RUNNING').count()
#            added = cache.add(key, val)
#            if added:
#                msg = "Added DB count for key %s : %d" % (key, val)
#                logging.debug(msg)
#            else:
#                msg = "Failed to decr key: %s" % key
#                logging.warn(msg)




    else:
        msg = "%s -> EXITING STATUSCODE: %s (WARN: state not RUNNING)" % (j.state, sc)
        element = "%f %s %s" % (time.time(), request.META['REMOTE_ADDR'], msg)
        red.rpush(j.jid, element)

        j.state = 'exiting'
        if sc:
            j.result = int(sc)
        j.flag = True
        j.save()


    elapsed = time.time() - start
    ss.timing(stat,int(elapsed))
    return HttpResponse("OK", mimetype="text/plain")

def action(request):
    """
    Update the latest factory actions
    """

    nick = request.POST.get('nick', None)
    fid = request.POST.get('fid', None)
    label = request.POST.get('label', None)
    txt = request.POST.get('msg', None)
    ip = request.META['REMOTE_ADDR']
    
    if not (nick and fid and label and txt):
        content = "Bad request"
        return HttpResponseBadRequest(content, mimetype="text/plain")

    txt = txt[:140]

    pq = get_object_or_404(BatchQueue, name=nick)

    f, created = Factory.objects.get_or_create(name=fid, defaults={'ip':ip})
    if created:
        msg = "Factory auto-created: %s" % fid
        logging.warn(msg)

    l, created = Label.objects.get_or_create(name=label, fid=f, batchqueue=pq)
    if created:
        msg = "Label auto-created: %s" % label
        logging.warn(msg)

    try:
        l.msg = txt
        l.save()
    except Exception, e:
        msg = "Failed to update label: %s" % l
        print msg, e
        return HttpResponseBadRequest(msg, mimetype="text/plain")

    return HttpResponse("OK", mimetype="text/plain")

def awol(request):
    """
    Handle jobs which have been lost within condor
    """

    jdecode = json.JSONDecoder()

    raw = request.POST.get('data', None)
    fid = request.POST.get('fid', None)

    if not (fid and raw):
        content = "Bad request"
        return HttpResponseBadRequest(content, mimetype="text/plain")

    try:
        data = jdecode.decode(raw)
        msg = "JSON list length: %d" % len(data)
        logging.debug(msg)
    except:
        msg = "Error decoding POST json data"
        logging.error(msg)
        content = "Bad request"
        return HttpResponseBadRequest(content, mimetype="text/plain")

    for cid in data:
        try:
            j = Job.objects.get(fid__name=fid, cid=cid)
        except Job.DoesNotExist:
            content = "DoesNotExist: %s" % cid
            return HttpResponseBadRequest(content, mimetype="text/plain")
    
        if j.state.name not in ['DONE', 'FAULT']:
            msg = "%s -> FAULT (AWOL)" % j.state
            element = "%f %s %s" % (time.time(), request.META['REMOTE_ADDR'], msg)
            red.rpush(j.jid, element)

            msg = "%s -> FAULT (AWOL) FID:%s CID:%s" % (j.state, j.fid, j.cid)
            logging.warn(msg)
            j.state = State.objects.get(name='FAULT')
            j.flag = True
            j.save()

    return HttpResponse("OK", mimetype="text/plain")

def ping(request, tag):
    """
    Log a ping request with timestamp and tag,
    """
    if len(tag) > 80:
        msg = tag[:77] + '...'
    else:
        msg = tag

    if request.is_secure():
        dn = request.META['HTTP_SSL_CLIENT_S_DN']
        dnok = request.META['HTTP_SSL_CLIENT_VERIFY']
        msg = dn+dnok
    else:
        dn = None
        dnok = False
    
    return HttpResponse("Pong! %s\n" % msg, mimetype="text/plain")

def cid(request, fid):
    """
    Return a list of jobs in state EXITING. This will allow condor_q
    to query the state of the condor job.
    """

#    jobs = Job.objects.filter(state__name='EXITING', fid__name=fid).order_by('last_modified')
    jobs = Job.objects.filter(state__name='EXITING', fid__name=fid).order_by('?')[:300]

    response = HttpResponse(mimetype='text/plain')

    writer = csv.writer(response)
    for j in jobs:
        writer.writerow([j.cid])

    return response

def old(request, fid):
    """
    Return a list of stale jobs
    """

    ip=request.META['REMOTE_ADDR']

    try:
        f = Factory.objects.get(name=fid)
    except Factory.DoesNotExist:
        msg = "factory %s not found" % fid
        logging.debug(msg)
        try:
            f = Factory.objects.get(ip=ip)
            msg = "found factory %s based on IP: %s" % (f, ip)
            logging.warning(msg)
        except Factory.DoesNotExist:
            msg = "factory IP not found: %s " % ip
            logging.error(msg)

    if not f:
        msg = "factory %s not found in function old()" % fid
        logging.error(msg)
        content = "Unknown factory: %s" % fid
        return HttpResponseBadRequest(content, mimetype="text/plain")

    deltat = datetime.now(pytz.utc) - timedelta(hours=24)
    cjobs = Job.objects.filter(fid=f, state='created', last_modified__lt=deltat)[:500]

    deltat = datetime.now(pytz.utc) - timedelta(hours=48)
    rjobs = Job.objects.filter(fid__name=fid, state__name='RUNNING', last_modified__lt=deltat)[:500]

    deltat = datetime.now(pytz.utc) - timedelta(hours=1)
    ejobs = Job.objects.filter(fid__name=fid, state__name='EXITING', last_modified__lt=deltat)[:500]

    jobs = []
    jobs.extend(cjobs)
    jobs.extend(rjobs)
# commented since we move to auto EXITING state
#    jobs.extend(ejobs)
    response = HttpResponse(mimetype='text/plain')

    writer = csv.writer(response)
    for j in jobs:
        writer.writerow([j.cid])

    return response

def fids(request):
    """
    Return list of all factories
    """

    fids = Factory.objects.all()

    response = HttpResponse(mimetype='text/plain')

    writer = csv.writer(response, delimiter=' ', lineterminator='\n')
    result = []
    for f in fids:
        result.append(f.id)

    writer.writerow(result)

    return response

def rrd(request):
    """
    Return list of active pandaqueues
    """

    pqs = BatchQueue.objects.all()

    response = HttpResponse(mimetype='text/plain')

    writer = csv.writer(response, delimiter=' ', lineterminator='\n')
    result = []
    for q in pqs:
        result.append(q.id)

    writer.writerow(result)

    return response

def pandasites(request):
    """
    Return list of active panda site names (siteid)
    """

    sites = Site.objects.all().distinct()

    queues = []
    for site in sites:
        qs = BatchQueue.objects.filter(site=site)
        queues += qs

    response = HttpResponse(mimetype='text/plain')

    writer = csv.writer(response)
    for q in queues:
        writer.writerow([q.wmsqueue])

    return response


#import rrdtool
#import StringIO
#import shutil
#import tempfile
#def img(request, t, fid, qid):
#    db = '/var/tmp/rrd/job-state-%s-%s.rrd' % (fid, qid)
#    t = str(t)
#    db = str(db)
#
#    # serialize to HTTP response
#    response = HttpResponse(mimetype="image/png")
#    f = tempfile.NamedTemporaryFile(dir='/dev/shm')
#
#    output = rrdtool.graph(f.name,
#            '--title', 'Hello',
#            '--watermark', 'x',
#            '--start', 'end-%s' % t,
#            '--lower-limit', '0',
#            '--vertical-label', "number of jobs" 
##            'DEF:cr=%s:created:AVERAGE' % db,
#            'DEF:cr=/var/tmp/rrd/job-state-1-1.rrd:created:AVERAGE',
#            'DEF:rn=%s:running:AVERAGE' % db,
#            'DEF:ex=%s:exiting:AVERAGE' % db,
#            'DEF:ft=%s:fault:AVERAGE' % db,
#            'DEF:dn=%s:done:AVERAGE' % db,
##            'CDEF:st1=cr,1,*',
#            'CDEF:st2=rn,1,*',
#            'CDEF:st3=ex,1,*',
#            'CDEF:st4=ft,1,*',
#            'CDEF:st5=dn,1,*',
#            'CDEF:ln1=cr,cr,UNKN,IF',
#            'CDEF:ln2=rn,cr,rn,+,UNKN,IF',
#            'CDEF:ln3=ex,rn,cr,ex,+,+,UNKN,IF',
#            'CDEF:ln4=ft',
#            'CDEF:ln5=dn',
#            'AREA:st1#ECD748:CREATED',
#            'STACK:st2#48C4EC:RUNNING',
#            'STACK:st3#EC9D48:EXITING',
#            'LINE1:ln1#C9B215',
#            'LINE1:ln2#1598C3',
#            'LINE1:ln3#CC7016',
#            'LINE3:ln4#cc3118:FAULT',
#            'LINE3:ln5#23bc14:DONE',
#            )
#
#    shutil.copyfileobj(f, response)
#    f.close()
#    return response

@cache_page(60 * 10)
def stats(request):
    """
    WTF
    """
    labels = Label.objects.all()

    lifetime = 300
    rows = []
    for l in labels:

        key = "ldn%d" % l.id
        val = cache.get(key)
        if val is None:
            msg = "MISS key: %s" % key
            logging.debug(msg)
            # key not known so set to current count
            val = Job.objects.filter(label=l, state__name='DONE').count()
            added = cache.add(key, val, lifetime)
            if added:
                msg = "Added DB count for key %s : %d" % (key, val)
                logging.debug(msg)
            else:
                msg = "Failed to add DB count for key %s : %d" % (key, val)
                logging.debug(msg)
        ndone = val

        key = "lft%d" % l.id
        val = cache.get(key)
        if val is None:
            msg = "MISS key: %s" % key
            logging.debug(msg)
            # key not known so set to current count
            val = Job.objects.filter(label=l, state__name='FAULT').count()
            added = cache.add(key, val, lifetime)
            if added:
                msg = "Added DB count for key %s : %d" % (key, val)
                logging.debug(msg)
            else:
                msg = "Failed to add DB count for key %s : %d" % (key, val)
                logging.debug(msg)
        nfault = val

        dt = datetime.now(pytz.utc)
        date = "%d-%02d-%02d" % (dt.year, dt.month, dt.day)
        # these need to come from Factory info
        out = "%s/%s/%s/%s.out"
        err = "%s/%s/%s/%s.err"
        log = "%s/%s/%s/%s.log"

        dir = str(l.name).translate(string.maketrans('/:','__'))

        logurl = "%s/%s/%s/" % (l.fid.url, date, dir)


        url = l.fid.url
        nhit = Job.objects.filter(state__name='DONE', label=l, result=0).count()
        nmiss = Job.objects.filter(state__name='DONE', label=l, result=20).count()
        row = {
            'label' : l.name,
            'labelid' : l.id,
            'factory' : l.fid.name,
            'factoryid' : l.fid.id,
            'factoryver' : l.fid.version,
            'pandaq' : l.pandaq.name,
            'pandaqid' : l.pandaq.id,
            'ndone' : ndone,
            'nfault' : nfault,
            'nhit' : nhit,
            'nmiss' : nmiss,
            'logurl' : logurl,
            'timestamp' : datetime.now(pytz.utc).strftime('%F %H:%M:%S UTC'),
            }
        rows.append(row)

    context = {
        'rows' : rows,
        }

    return HttpResponse(json.dumps(rows, sort_keys=True, indent=2), mimetype="application/json")


def test(request):

    jobs = Job.objects.all()

    context = {}
    return render_to_response('mon/test.html', context)

#@cache_page(60 * 1)
def index(request):
    """
    Rendered view of front page which shows a table of activity
    for each factories
    """
    jobs = Job.objects.all()
    dtfail = datetime.now(pytz.utc) - timedelta(days=10)
    dterror = datetime.now(pytz.utc) - timedelta(hours=1)
    dtwarn = datetime.now(pytz.utc) - timedelta(minutes=20)

    factories = Factory.objects.all().order_by('name')
    rows = []
    for f in factories:
        if f.last_modified < dtfail: continue

        # this 'active' string map to a html classes
        active = 'error'
        if f.last_modified > dterror:
            active = 'warn'
        if f.last_modified > dtwarn:
            active = 'ok'
        row = {
            'factory' : f,
            'active' : active,
            }

        rows.append(row)

    context = {
            'rows' : rows,
            }

    return render_to_response('mon/index.html', context)

def cloud(request, name):
    """
    Rendered view of Cloud page showing table of Sites in this cloud.
    """
    sites = Site.objects.filter(cloud=name)

    labels = Label.objects.filter(batchqueue__wmsqueue__site__cloud=name)
    dtwarn = datetime.now(pytz.utc) - timedelta(minutes=20)

    factive = []
    finactive = []
    for label in labels:
        if label.fid not in factive + finactive:
            if label.fid.last_modified > dtwarn:
                factive.append(label.fid)
            else:
                finactive.append(label.fid)

    nrunning = 0
    rows = []

    for site in sites:

        pandaqs = BatchQueue.objects.filter(wmsqueue__site=site)
        for pandaq in pandaqs:

            elogmatch = ELOGREGEX.match(pandaq.comment)
            ggusmatch = GGUSREGEX.match(pandaq.comment)
            savmatch = SAVANNAHREGEX.match(pandaq.comment)
            url = prefix = suffix = None
            if elogmatch:
                prefix = elogmatch.group(1)
                suffix = elogmatch.group(2)
                url = ELOGURL % suffix
            elif ggusmatch:
                prefix = ggusmatch.group(1)
                suffix = ggusmatch.group(2)
                url = GGUSURL % suffix 
            elif savmatch:
                prefix = savmatch.group(1)
                suffix = savmatch.group(2)
                url = SAVANNAHURL % suffix

            jobs = Job.objects.filter(label__batchqueue=pandaq)

            cssclass = pandaq.state 
            if pandaq.type in ['SPECIAL_QUEUE']:
                cssclass = 'mute'

            row = {
                    'site' : site,
                    'url' : url,
                    'prefix' : prefix,
                    'suffix' : suffix,
                    'pandaq' : pandaq,
#                    'running' : nrunning,
                    'class' : cssclass,
                    }
            rows.append(row)

    context = {
            'factive' : factive,
            'finactive' : finactive,
            'cloud' : name,
            'sites' : sites,
            'rows' : rows,
            }


    return render_to_response('mon/cloud.html', context)

def testtimeline(request):

    jobs = Job.objects.filter(label__name='UKI-NORTHGRID-LANCS-HEP-abaddon-cream').order_by('-last_modified')

    context = {
            'jobs' : jobs[:10],
            }

    return render_to_response('mon/test.html', context)

@cache_page(60 * 10)
def queues(request):
    """
    Rendered view of all queues, all factories.
    """

    # cache lifetime for pandaq state counts
    lifetime = 300

    clouds = Site.objects.values_list('cloud', flat=True).order_by('cloud').distinct()
    pandaqs = BatchQueue.objects.filter().order_by('wmsqueue__site__cloud','name')
    dt = datetime.now(pytz.utc) - timedelta(hours=1)
    jobs = Job.objects.all()

    cloudlist = []
    for cloud in clouds:
        npq = BatchQueue.objects.filter(wmsqueue__site__cloud=cloud).count()
        cloudlist.append({'name' : cloud, 'npq' : npq})

    rows = []
    for pandaq in pandaqs:
        labs = Label.objects.filter(batchqueue=pandaq)
        nactive = 0
        ndone = 0
        nfault = 0
        
        # ACTIVE job count from cache
        key = "pq%d%s" % (pandaq.id, 'astate')
        val = cache.get(key)
        if val is None:
            # key not known so set to current count
            msg = "MISS key: %s" % key
            logging.debug(msg)
            jobs = jobs.filter(label__batchqueue=pandaq)
            jobs = jobs.filter(state__in=['created','running','exiting'])
            val = jobs.count()
            added = cache.add(key, val, lifetime)
            if added:
                msg = "Added DB count for key %s : %d" % (key, val)
                logging.warn(msg)
            else:
                msg = "queues() failed to add DB count for key %s : %d" % (key, val)
                logging.warn(msg)
        nactive = val

        # DONE job count from cache
        key = "pq%d%s" % (pandaq.id, 'dstate')
        val = cache.get(key)
        if val is None:
            # key not known so set to current count
            msg = "MISS key: %s" % key
            logging.debug(msg)
            val = jobs.filter(label__batchqueue=pandaq, state="done").count()
            added = cache.add(key, val, lifetime)
            if added:
                msg = "Added DB count for key %s : %d" % (key, val)
                logging.warn(msg)
            else:
                msg = "Failed to add DB count for key %s : %d" % (key, val)
                logging.warn(msg)
        ndone = val

        # FAULT job count from cache
        key = "pq%d%s" % (pandaq.id, 'fstate')
        val = cache.get(key)
        if val is None:
            # key not known so set to current count
            msg = "MISS key: %s" % key
            logging.debug(msg)
            val = jobs.filter(label__batchqueue=pandaq, state="fault").count()
            added = cache.add(key, val, lifetime)
            if added:
                msg = "Added DB count for key %s : %d" % (key, val)
                logging.warn(msg)
            else:
                msg = "Failed to add DB count for key %s : %d" % (key, val)
                logging.warn(msg)
        nfault = val

        row = {
            'pandaq'     : pandaq,
            'nactive'    : nactive,
            'ndone'      : ndone,
            'nfault'     : nfault,
            }

        rows.append(row)

    fids = []       
    context = {
            'clouds'    : clouds,
            'rows'      : rows,
            'factories' : fids,
            }

    return render_to_response('mon/queues.html', context)

def shout(request):
    """
    Create the Job
    """

    jdecode = json.JSONDecoder()

    raw = request.POST.get('data', None)

    
    if raw:
        data = jdecode.decode(raw)
        for d in data:
            logging.warn(d)


    
    return HttpResponse("OK", mimetype="text/plain")

def cr(request):
    """
    Create the Job, expect data format is:
    (cid, nick, fid, label)
    """
    stat = 'apfmon.cr'
    start = time.time()

    ip = request.META['REMOTE_ADDR']
    jdecode = json.JSONDecoder()

    raw = request.POST.get('data', None)

    if not raw:
        msg = 'No POST data found'
        logging.error(msg)
        content = "Bad request, no POST data found"
        return HttpResponseBadRequest(content, mimetype="text/plain")

    try:
        data = jdecode.decode(raw)
        ncreated = len(data)
        msg = "Number of jobs in JSON data: %d (%s)" % (ncreated, ip)
        logging.warn(msg)
    except:
        msg = 'Error decoding POST json data'
        logging.error(msg)
        content = "Bad request"
        return HttpResponseBadRequest(content, mimetype="text/plain")

    for d in data:
        cid = d[0]
        nick = d[1]
        fid = d[2]
        label = d[3]
    
        pq, created = BatchQueue.objects.get_or_create(name=nick)
        if created:
            msg = 'FID:%s, BatchQueue auto-created, no siteid: %s' % (fid,nick)
            logging.error(msg)
            pq.save()
    
        f, created = Factory.objects.get_or_create(name=fid, defaults={'ip':ip})
        if created:
            msg = "Factory auto-created: %s" % fid
            logging.error(msg)
        f.last_ncreated = ncreated
        f.save()
    
        try: 
            l = Label.objects.get(name=label, fid=f, batchqueue=pq)
        except:
            msg = 'PAL except:'
            logging.error(msg)
            l = Label(name=label, fid=f, batchqueue=pq)
            created = True
            
#        try:
#            l, created = Label.objects.get_or_create(name=label, fid=f, pandaq=pq)
#        except MultipleObjectsReturned,e:
#            msg = "Multiple objects - apfv2 issue?"
#            logging.error(msg)
#            msg = "Multiple objects error"
#            return HttpResponseBadRequest(msg, mimetype="text/plain")

        if created:
            msg = "Label auto-created: %s" % label
            logging.error(msg)
    
        try:
            jid = ':'.join((f.name,cid))
            j = Job(jid=jid, cid=cid, state='created', label=l)
            j.save()

            key = "fcr%d" % f.id
            try:
                val = cache.incr(key)
            except ValueError:
                msg = "MISS key: %s" % key
                logging.warn(msg)
                # key not known so set to current count
                val = Job.objects.filter(jid__startswith=f.name, state='created').count()
                added = cache.add(key, val)
                if added:
                    msg = "Added DB count for key %s : %d" % (key, val)
                    logging.warn(msg)
                else:
                    msg = "Failed to incr key: %s" % key
                    logging.warn(msg)

            if not val % 1000:
                msg = "memcached key:%s val:%d" % (key, val)
                logging.warn(msg)
        except Exception, e:
            msg = "Failed to create: fid=%s cid=%s state=created label=%s" % (f,cid,l)
            logging.error(e)
            logging.error(msg)
            return HttpResponseBadRequest(msg, mimetype="text/plain")
    
    elapsed = time.time() - start
    ss.timing(stat,int(elapsed))

    txt = 'job' if len(data) == 1 else 'jobs'
    context = 'Received %d %s' % (len(data), txt) 
    return HttpResponse(context, mimetype="text/plain")

def helo(request):
    """
    Factory startup messages. Expecting POST with key,value pairs
    Known and used keys:
    factoryId
    monitorURL
    factoryOwner
    baseLogDirUrl
    versionTag

    """
    fid = request.POST.get('factoryId', None)
    owner = request.POST.get('factoryOwner', None)
    url = request.POST.get('baseLogDirUrl', None)
    ip = request.META['REMOTE_ADDR']
    ver = request.POST.get('versionTag', None)

    logging.debug(fid)
    logging.debug(owner)
    logging.debug(url)
    logging.debug(ip)

    if not (fid and owner and url):
        content = "Bad request"
        return HttpResponseBadRequest(content, mimetype="text/plain")

    d = {'ip' : ip,
         'url' : url,
         'email' : owner,
         'last_startup' : datetime.now(pytz.utc),
         'version' : ver,
        }

    f, created = Factory.objects.get_or_create(name=fid, defaults=d)
    if created:
        msg = "Factory auto-created: %s" % fid
        logging.info(msg)
        mail_managers('New factory: %s' % fid,
                      'New factory: %s' % fid,
                      fail_silently=False)


    f.ip = ip
    f.url = url
    f.email = owner
    f.last_startup = datetime.now(pytz.utc)
    f.version = ver
    f.save()

    return HttpResponse("OK", mimetype="text/plain")

def msg(request):
    """
    Update the latest factory messages. Expect data format:
    (nick, fid, label, text)
    """

    ip=request.META['REMOTE_ADDR']

    jdecode = json.JSONDecoder()

    cycle = request.POST.get('cycle', None)
    raw = request.POST.get('data', None)
    
    if raw:
        try:
            data = jdecode.decode(raw)
            msg = "Number of msgs in JSON data: %d (%s)" % (len(data), ip)
            logging.debug(msg)
            length = request.META['CONTENT_LENGTH']
            msg = "Msg content length: %s" % length
            logging.info(msg)
        except:
            msg = 'Error decoding POST json data'
            logging.error(msg)
            content = "Bad request"
            return HttpResponseBadRequest(content, mimetype="text/plain")

        for d in data:
            nick = d[0]
            fid = d[1]
            label = d[2]
            text = d[3]

            txt = text[:140]
        
            pq, created = BatchQueue.objects.get_or_create(name=nick)
            if created:
                msg = 'FID:%s, BatchQueue auto-created, no siteid: %s' % (fid,nick)
                logging.warn(msg)
                pq.save()

            ip = request.META['REMOTE_ADDR']
            f, created = Factory.objects.get_or_create(name=fid, defaults={'ip':ip})
            if created:
                msg = "Factory auto-created: %s" % fid
                logging.warn(msg)
            if cycle:
                f.last_cycle = cycle
            f.save()
        

            try:
                l = Label.objects.get(name=label, fid=f, batchqueue=pq)
            except:
                msg = 'PAL except msg() pq:%s' % pq
                logging.error(msg)
                l = Label(name=label, fid=f, batchqueue=pq)
                created = True

#            try:
#                l, created = Label.objects.get_or_create(name=label, fid=f, pandaq=pq)
#            except MultipleObjectsReturned, e:
#                msg = "Multiple objects apfv2 error %s %s" %(ip, dict(request.POST))
#                logging.warn(msg)
#                logging.warn(str(e))
#                msg = "Multiple objects error %s %s" %(ip, dict(request.POST))
#                return HttpResponseBadRequest(msg, mimetype="text/plain")

            if created:
                msg = "Label auto-created: %s" % label
                logging.warn(msg)
#            l = get_object_or_404(Label, name=label, fid=f, pandaq=pq)
        
            try:
                l.msg = txt
                l.save()
            except Exception, e:
                msg = "Failed to update the %s label: %s" % (created,l)
                logging.error(msg)
                logging.error(e)
                return HttpResponseBadRequest(msg, mimetype="text/plain")

    return HttpResponse("OK", mimetype="text/plain")

def help(request):

    context = {}
    return render_to_response('mon/help.html', context)


def search(request):
    """
    Search for a string in pandaqueue, sites, labels.
    """

    query = request.GET.get('q', '')

    # see Simple generic views in django docs

    url = reverse('apfmon.mon.views.query', args=(query,))
    logging.debug(url)
    return HttpResponseRedirect(url)

def query(request, q=None):
    """
    Search for a string in pandaq
    """
    if q:
        qset = (
            Q(name__icontains=q) |
            Q(batchqueue__name__icontains=q) |
            Q(batchqueue__wmsqueue__name__icontains=q) |
            Q(batchqueue__wmsqueue__site__name__icontains=q)
            # can add other search params here, eg. SITE name
        )
        labels = Label.objects.filter(qset).order_by('fid', 'name')
    else:
        labels = []

    context = {
        'labels' : labels,
        'query'  : q,
    }
    return render_to_response('mon/query.html', context)


def site(request, sid):
    """
    Rendered view of Site page showing table of Pandaqs for this Site
    including stats from all factories
    Note: this is a Site not a PandaSite
    """
    s = get_object_or_404(Site, id=int(sid))
    dt = datetime.now(pytz.utc) - timedelta(hours=1)

    # all labels serving this site
    labels = Label.objects.filter(batchqueue__wmsqueue__site=s)

    rows = []
    for label in labels:
        row = {}
        ncreated = 0
        nsubmitted = 0
        nrunning = 0
        nexiting = 0
        ndone = 0
        nfault = 0
        nmiss = 0
        jobs = Job.objects.filter(label=label)
    
        row['jobcount'] = {
                'created' : ncreated,
                'running' : nrunning,
                'exiting' : nexiting,
                'done' : ndone,
                'fault' : nfault,
                'miss' : nmiss,
                }

        row['label'] = label
        pandaqs = BatchQueue.objects.filter(label=label)
        rows.append(row)

    context = {
            'site' : s,
            'rows' : rows,
            }


    return render_to_response('mon/site.html', context)

def fault(request):
    """
    List Labels which have FAULT jobs
    """

    jobs = Job.objects.filter(state='fault', label__batchqueue__state='online')
    labels = jobs.values('label__id', 'label__batchqueue').annotate(njob=Count('id'))

    rows = []
    for lab in labels:
        lid = lab['label__id']
        nfault = lab['njob']
        if nfault < 1: continue
        nflag = Job.objects.filter(label=lid, flag=True).count()
        totjob = Job.objects.filter(label=lid).count()
        flagfrac = 100 * nflag/totjob
        faultfrac = 100 * nfault/totjob

        try:
            label = Label.objects.get(id=lid)
        except Label.DoesNotExist:
            msg = 'Label does not exist: %s' % lid
            logging.warn(msg)
            continue
        
        row = {
            'label' : label,
            'flagfrac' : flagfrac,
            'faultfrac' : faultfrac,
            'totjob' : totjob,
            }
        rows.append(row)

    # find panda queues only being serviced by one factory
    qlist = Label.objects.values('batchqueue__name','batchqueue__id').annotate(n=Count('fid'))
    sololist = []
    for q in qlist:
        if q['n'] == 1:
            sololist.append(q)

    sortedrows = sorted(rows, key=itemgetter('flagfrac'), reverse=True) 
    context = {
        'rows' : sortedrows[:20],
        'sololist' : sololist,
        }

    return render_to_response('mon/fault.html', context)

def labels(request):
    """
    Rendered view of all Labels
    """

    jobs = Job.objects.all()
    lablist = Label.objects.all()

    stale = datetime.now(pytz.utc) - timedelta(days=14)

    rows = []
    for lab in lablist:
        activity = 'ok'
        if stale > lab.last_modified:
            activity = 'stale'
        row = {
            'label' : lab,
            'last_modified' : lab.last_modified,
            'activity' : activity,
            }
        rows.append(row)

    sortedrows = sorted(rows, key=itemgetter('last_modified')) 
    context = {
        'rows' : sortedrows,
        }

    return render_to_response('mon/labels.html', context)

def label(request, lid, p=1):
    """
    Rendered view of a single Label with job details
    """

    l = get_object_or_404(Label, id=lid)

    dt = datetime.now(pytz.utc) - timedelta(hours=1)
    # factories with labels serving selected pandaq

    row = {}
    ncreated = 0
    nsubmitted = 0
    nrunning = 0
    nexiting = 0
    ndone = 0
    nfault = 0

    jobs = Job.objects.filter(label=l)
    ncreated = jobs.filter(state='created').count()
    nrunning = jobs.filter(state='running').count()
    nexiting = jobs.filter(state='exiting').count()
    ndone = jobs.filter(state='done').count()
    nfault = jobs.filter(state='fault').count()
    nmiss = jobs.filter(state='done', result=20).count()
    
    row['jobcount'] = {
            'created' : ncreated,
            'running' : nrunning,
            'exiting' : nexiting,
            'done' : ndone,
            'fault' : nfault,
            'miss' : nmiss,
            }

    row['label'] = l
    
    statdone = 'pass'
    if nexiting == 0:
        statdone = 'fail'
    elif nexiting <= 5:
        statdone = 'warn'
    
    statfault = 'hot'
    if nfault == 0:
        statfault = 'pass'

    row['statdone'] = statdone
    row['statfault'] = statfault

    activewarn = datetime.now(pytz.utc) - timedelta(minutes=5)
    activeerror = datetime.now(pytz.utc) - timedelta(minutes=10)
    row['activity'] = 'ok'
    if activewarn > l.last_modified:
        row['activity'] = 'warn'
    if activeerror > l.last_modified:
        row['activity'] = 'fail'

    pages = Paginator(Job.objects.filter(label=lid).order_by('-last_modified'), 200)
    jobs = Job.objects.filter(label=lid).order_by('-last_modified')[:200]

    context = {
            'label' : l,
            'pandaq' : l.batchqueue,
            'row' : row,
            'jobs' : jobs,
            'pages' : pages,
            'page' : pages.page(p),
            }

    return render_to_response('mon/label.html', context)

def cloudindex(request):
    """
    Rendered view which shows a table of activity
    for each cloud with counts of number of active factories
    """

    clouds = Site.objects.values_list('cloud', flat=True).order_by('cloud').distinct()
    dt = datetime.now(pytz.utc) - timedelta(minutes=10)
    dtfail = datetime.now(pytz.utc) - timedelta(hours=1)
    dtwarn = datetime.now(pytz.utc) - timedelta(minutes=20)
    dtdead = datetime.now(pytz.utc) - timedelta(days=10)

    crows = []
    #    labels = Label.objects.all()
    for cloud in clouds:

        factive = []
        labels = Label.objects.filter(batchqueue__wmsqueue__site__cloud=cloud)

        factories = []
        ncreated = 0
        for label in labels:
            if label.fid not in factories:
                if label.fid.last_modified < dtdead: continue
                factories.append(label.fid)
                if label.fid.last_modified > dtwarn:
                    factive.append(label.fid)

        row = {
            'cloud'     : cloud,
            'labels'    : labels,
            'factories' : factories,
            'factive'   : factive,
            'ncreated'  : ncreated,
            }

        crows.append(row)

    context = { 'crows' : crows }

    return render_to_response('mon/cloudindex.html', context)

