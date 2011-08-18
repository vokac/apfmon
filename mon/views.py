from atl.mon.models import State
from atl.mon.models import Factory
from atl.mon.models import Job
from atl.mon.models import Label
from atl.mon.models import Message
from atl.mon.models import Pandaid

from atl.kit.models import Tag
from atl.kit.models import Site
from atl.kit.models import PandaQueue

import csv
import logging
import string
import sys
from operator import itemgetter
from datetime import timedelta, datetime
from django.shortcuts import redirect, render_to_response, get_object_or_404
from django.db.models import Count
from django.db.models import Q
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.http import HttpResponseRedirect
from django.core.mail import send_mail
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.urlresolvers import reverse

try:
    import json as json
except ImportError, err:
    import simplejson as json

# Flows
# 1. CREATED <- condor_id (Entry)
# 3. RUNNING <- signal from pilot-wrapper
# 4. EXITING <- signal from pilot-wrapper
# 5. DONE <- signal from cronjob script (mon-exiting.py) jobstate=4

def jobs(request, lid, state, p=1):
    """
    Rendered view of a set of Jobs for particular Label and optional State
    """

    l = get_object_or_404(Label, id=int(lid))
    if state == 'ACTIVE':
        s = None
        states = ['CREATED','RUNNING','EXITING']
    else:
        s = get_object_or_404(State, name=state)
        states = [s.name]

    jobs = Job.objects.filter(label=l).order_by('-last_modified')

    dt = datetime.now() - timedelta(hours=1)
    if s:
        if s.name in ['DONE', 'FAULT']:
            jobs = jobs.filter(state=s, last_modified__gt=dt)
        else:
            jobs = jobs.filter(state=s)
    else:
        jobs = jobs.filter(state__name__in=['CREATED','RUNNING','EXITING'])

    
    pages = Paginator(jobs, 25)

    try:
        page = pages.page(p)
    except (EmptyPage, InvalidPage):
        page = pages.page(pages.num_pages)

    context = {
                'label' : l,
                'name' : l.name,
                'factoryname' : l.fid.name,
                'fid' : l.fid.id,
                'pandaq' : l.pandaq,
                'statename' : state,
                'states' : states,
                'jobs' : jobs,
                'pages' : pages,
                'page' : page,
                'dt' : dt,
                }

    return render_to_response('mon/jobs.html', context)

def jobsold(request, fid, qid, state, p=1):
    """
    Rendered view of a set of Jobs for particular Factory, PandaQueue,
    and optional State
    """

    try:
        f = Factory.objects.get(id=int(fid))
    except Factory.DoesNotExist:
        f = None
        
    q = get_object_or_404(PandaQueue, id=int(qid))
    if state == 'ACTIVE':
        s = None
        states = ['CREATED','RUNNING','EXITING']
    else:
        s = get_object_or_404(State, name=state)
        states = [s.name]

    dt = datetime.now() - timedelta(hours=1)
    if f:
        jobs = Job.objects.filter(pandaq=q, fid=f).order_by('-last_modified')
        factoryname = f.name
    else:
        jobs = Job.objects.filter(pandaq=q).order_by('-last_modified')
        factoryname = 'All'
        

    if s:
        if s.name in ['DONE', 'FAULT']:
            jobs = jobs.filter(state=s, last_modified__gt=dt)
        else:
            jobs = jobs.filter(state=s)
    else:
        jobs = jobs.filter(state__name__in=['CREATED','RUNNING','EXITING'])

    
    pages = Paginator(jobs, 25)

    context = {
                'factoryname' : factoryname,
                'fid' : fid,
                'pandaq' : q,
                'name' : q.name,
                'statename' : state,
                'states' : states,
                'jobs' : jobs,
                'pages' : pages,
                'page' : pages.page(p),
                'dt' : dt,
                }

    return render_to_response('mon/jobs.html', context)

def job(request, fid, cid):
    """
    Rendered view of job information
    """

    # handle Factory id and name
    try:
        id = int(fid)
        f = get_object_or_404(Factory, id=id)
    except ValueError:
        f = get_object_or_404(Factory, name=fid)
        
    job = get_object_or_404(Job, fid=f, cid=cid)

    pids = Pandaid.objects.filter(job=job)
    msgs = Message.objects.filter(job=job).order_by('received')

    date = "%d-%02d-%02d" % (job.created.year, job.created.month, job.created.day)
    # these need to come from Factory info
    out = "%s/%s/%s/%s.out"
    err = "%s/%s/%s/%s.err"
    log = "%s/%s/%s/%s.log"

    dir = str(job.label).translate(string.maketrans('/:','__'))

    outurl = out % (f.url, date, dir, job.cid)
    errurl = err % (f.url, date, dir, job.cid)
    logurl = log % (f.url, date, dir, job.cid)

    context = {
                'outurl' : outurl,
                'errurl' : errurl,
                'logurl' : logurl,
                'job' : job,
                'msgs' : msgs,
                'pids' : pids,
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

    dt = datetime.now() - timedelta(minutes=60)
    fault = Job.objects.filter(last_modified__gt=dt, state__name='FAULT')
    done = Job.objects.filter(last_modified__gt=dt, state__name='DONE').filter(result=0)
    flagged = Job.objects.filter(last_modified__gt=dt, flag=True)
    havejob = done.filter(result=0)

    dt = datetime.now() - timedelta(hours=48)
    ancient = Job.objects.filter(created__lt=dt).order_by('created').exclude(state__name__in=['FAULT','DONE'])

    context = {
                'ancient' : ancient,
                'flagged' : flagged,
                'fault' : fault,
                'done' : done,
                'havejob' : havejob,
                }

    return render_to_response('mon/debug.html', context)

def factory(request, fid):
    """
    Rendered view of Factory instance. Lists all factory labels with
    a count of jobs in each state.
    """
    if not int(fid): return redirect('atl.mon.views.index')
    f = get_object_or_404(Factory, id=int(fid))
    pandaqs = PandaQueue.objects.all()
    labels = Label.objects.filter(fid=f)
    jobs = Job.objects.filter(fid=f)
    dt = datetime.now() - timedelta(hours=1)

    cstate = State.objects.get(name='CREATED')
    rstate = State.objects.get(name='RUNNING')
    estate = State.objects.get(name='EXITING')
    dstate = State.objects.get(name='DONE')
    fstate = State.objects.get(name='FAULT')

    rows = []
    for lab in labels:
        ncreated = 0
        nsubmitted = 0
        nrunning = 0
        nexiting = 0
        ndone = 0
        nfault = 0
        ncreated = jobs.filter(label=lab, state=cstate).count()
        nrunning = jobs.filter(label=lab, state=rstate).count()
        nexiting = jobs.filter(label=lab, state=estate).count()
#        ndone = jobs.filter(label=lab, state=dstate, last_modified__gt=dt).count()
#        nfault = jobs.filter(label=lab, state=fstate, last_modified__gt=dt).count()

        statcr = 'pass'
        if ncreated >= 1000:
            statcr = 'warn'

        statdone = 'pass'
        if ndone <= 0:
            statdone = 'warn'

        statfault = 'pass'
        if nfault >= 50:
            statfault = 'hot'

        activewarn = datetime.now() - timedelta(minutes=5)
        activeerror = datetime.now() - timedelta(minutes=10)
        activity = 'ok'
        if activewarn > lab.last_modified:
            activity = 'warn'
        if activeerror > lab.last_modified:
            activity = 'note'
    
        row = {
            'label' : lab,
            'pandaq' : lab.pandaq,
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
            'plot' : 'on',
            }

    return render_to_response('mon/factory.html', context)

def pandaq(request, qid, p=1):
    """
    Rendered view of panda queue for all factories
    """

    q = get_object_or_404(PandaQueue, id=qid)

    labels = Label.objects.filter(pandaq=q)
    dt = datetime.now() - timedelta(hours=1)
    # factories with labels serving selected pandaq
    fs = Factory.objects.filter(label__in=labels)

    cstate = State.objects.get(name='CREATED')
    rstate = State.objects.get(name='RUNNING')
    estate = State.objects.get(name='EXITING')
    dstate = State.objects.get(name='DONE')
    fstate = State.objects.get(name='FAULT')

    rows = []
    for lab in labels:
        row = {}
        ncreated = 0
        nsubmitted = 0
        nrunning = 0
        nexiting = 0
        ndone = 0
        nfault = 0
        jobs = Job.objects.filter(label=lab)
        ncreated = jobs.filter(state=cstate).count()
        nrunning = jobs.filter(state=rstate).count()
        nexiting = jobs.filter(state=estate).count()
        ndone = jobs.filter(state=dstate, last_modified__gt=dt).count()
        nfault = jobs.filter(state=fstate, last_modified__gt=dt).count()
        nmiss = jobs.filter(state=dstate, last_modified__gt=dt, result=20).count()
    
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

        activewarn = datetime.now() - timedelta(minutes=5)
        activeerror = datetime.now() - timedelta(minutes=10)
        row['activity'] = 'ok'
        if activewarn > lab.last_modified:
            row['activity'] = 'warn'
        if activeerror > lab.last_modified:
            row['activity'] = 'fail'

        rows.append(row)

    pages = Paginator(Job.objects.filter(pandaq=qid).order_by('-last_modified'), 50)
    jobs = Job.objects.filter(pandaq=qid).order_by('-last_modified')[:50]

    context = {
            'pandaq' : q,
            'rows' : rows,
            'jobs' : jobs,
            'pages' : pages,
            'page' : pages.page(p),
            'plot' : 'off',
            }

    return render_to_response('mon/pandaq.html', context)

def oldindex(request):
    """
    Rendered view of front mon page
    """

    factories = Factory.objects.all()
   
    dt = datetime.now() - timedelta(hours=1)
    jobs = Job.objects.all()

    cstate = State.objects.get(name='CREATED')
    rstate = State.objects.get(name='RUNNING')
    estate = State.objects.get(name='EXITING')
    dstate = State.objects.get(name='DONE')
    fstate = State.objects.get(name='FAULT')

    rows = []
    for f in factories:
        ncreated = 0
        nrunning = 0
        nexiting = 0
        ndone = 0
        nfault = 0
        ntotal = jobs.count()
        ncreated = jobs.filter(fid=f, state=cstate).count()
        nrunning = jobs.filter(fid=f, state=rstate).count()
        nexiting = jobs.filter(fid=f, state=estate).count()
        ndone = jobs.filter(fid=f, state=dstate, last_modified__gt=dt).count()
        nfault = jobs.filter(fid=f, state=fstate, last_modified__gt=dt).count()
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
            q = PandaQueue.objects.get(id=qid)
        except PandaQueue.DoesNotExist:
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
            jobs = Job.objects.filter(fid=f, state=s, pandaq=q)
        elif s:
            jobs = Job.objects.filter(fid=f, state=s)
        elif q:
            jobs = Job.objects.filter(fid=f, pandaq=q)
        else:
            jobs = Job.objects.filter(fid=f)
    else:
        if q and s:
            jobs = Job.objects.filter(state=s, pandaq=q)
        elif s:
            jobs = Job.objects.filter(state=s)
        elif q:
            jobs = Job.objects.filter(pandaq=q)
        else:
            jobs = Job.objects.all()


    if state in ['FAULT', 'DONE']:
        deltat = datetime.now() - timedelta(hours=1)
        jobs = jobs.filter(last_modified__gt=deltat)

    result = jobs.count()

    return HttpResponse("%s" % result, mimetype="text/plain")

def st(request):
    """
    Unrendered handle reported state of condor job, via mon-exiting.py cron

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
        m = Message(job=j, msg=msg, client=request.META['REMOTE_ADDR'])
        m.save()
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
            m = Message(job=j, msg=msg, client=request.META['REMOTE_ADDR'])
            m.save()

    return HttpResponse("OK", mimetype="text/plain")

def staleold(request):
    """
    Handle job which has been too long in a particular state
    Called by the mon-stale.py cronjob using jobs given by old() func
    """

    fid = request.POST.get('fid', None)
    cid = request.POST.get('cid', None)
    js = request.POST.get('js', None)
    gs = request.POST.get('gs', None)

    if not (fid and cid):
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
        m = Message(job=j, msg=msg, client=request.META['REMOTE_ADDR'])
        m.save()

    return HttpResponse("OK", mimetype="text/plain")

def cr(request):
    """
    Create the Job
    """

    cid = request.POST.get('cid', None)
    nick = request.POST.get('nick', None)
    fid = request.POST.get('fid', None)
    label = request.POST.get('label', None)
    ip = request.META['REMOTE_ADDR']
    
    if not (cid and nick and fid and label):
        content = "Bad request"
        return HttpResponseBadRequest(content, mimetype="text/plain")

    pq, created = PandaQueue.objects.get_or_create(name=nick)
    if created:
        msg = "PandaQueue auto-created: %s" % nick
        logging.warn(msg)

    f, created = Factory.objects.get_or_create(name=fid, defaults={'ip':ip})
    if created:
        msg = "Factory auto-created: %s" % fid
        logging.warn(msg)

    l, created = Label.objects.get_or_create(name=label, fid=f, pandaq=pq)
    if created:
        msg = "Label auto-created: %s" % label
        logging.warn(msg)

    try:
        state = State.objects.get(name='CREATED')
        j = Job(cid=cid, fid=f, state=state, pandaq=pq, label=l)
        j.save()
    except Exception, e:
        msg = "Failed to create: %s_%s" % (f, cid)
        print msg, e
        return HttpResponseBadRequest(msg, mimetype="text/plain")

    msg = "CREATED"
    m = Message(job=j, msg=msg, client=request.META['REMOTE_ADDR'])
    m.save()

    return HttpResponse("OK", mimetype="text/plain")

def rn(request, fid, cid):
    """
    Handle 'rn' signal from a running job
    """

    try:
        j = Job.objects.get(cid=cid, fid__name=fid)
    except Job.DoesNotExist, e:
        msg = "RN unknown Job: %s_%s" % (fid, cid)
        logging.warn(msg)
        content = "Fine"
        return HttpResponseBadRequest(content, mimetype="text/plain")

    msg = None

    if j.state.name == 'CREATED':
        msg = "%s -> RUNNING" % j.state
        j.state = State.objects.get(name='RUNNING')
        j.save()

    else:
        msg = "%s -> RUNNING (WARN: state not CREATED)" % j.state
        j.state = State.objects.get(name='RUNNING')
        j.flag = True
        j.save()

    if msg:
        m = Message(job=j, msg=msg, client=request.META['REMOTE_ADDR'])
        m.save()

    return HttpResponse("OK", mimetype="text/plain")

def ex(request, fid, cid, sc):
    """
    Handle 'ex' signal from exiting wrapper
    """
    
    if not sc: sc=None

    try:
        j = Job.objects.get(fid__name=fid, cid=cid)
    except Job.DoesNotExist, e:
        msg = "EX unknown Job: %s_%s" % (fid, cid)
        logging.warn(msg)
        return HttpResponseBadRequest('Fine', mimetype="text/plain")
    
    msg = None

    if j.state.name in ['DONE', 'FAULT']:
        msg = "Terminal: %s, no state change allowed." % j.state
        j.flag = True
        j.save()

    elif j.state.name == 'RUNNING':
        msg = "%s -> EXITING STATUSCODE: %s" % (j.state, sc)
        j.state = State.objects.get(name='EXITING')
        if sc:
            j.result = (sc)
        else:
            j.flag = True
        j.save()

    else:
        msg = "%s -> EXITING STATUSCODE: %s (WARN: state not RUNNING)" % (j.state, sc)
        j.state = State.objects.get(name='EXITING')
        if sc:
            j.result = int(sc)
        j.flag = True
        j.save()

    if msg:
        m = Message(job=j, msg=msg, client=request.META['REMOTE_ADDR'])
        m.save()

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

    pq, created = PandaQueue.objects.get_or_create(name=nick)
    if created:
        msg = "PandaQueue auto-created: %s" % nick
        logging.warn(msg)

    f, created = Factory.objects.get_or_create(name=fid, defaults={'ip':ip})
    if created:
        msg = "Factory auto-created: %s" % fid
        logging.warn(msg)

    l, created = Label.objects.get_or_create(name=label, fid=f, pandaq=pq)
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

def info(request, fid, cid):
    """
    Handle info about the panda job, find pandaID
    """

    try:
        j = Job.objects.get(fid__name=fid, cid=cid)
    except Job.DoesNotExist, e:
        msg = "INF unknown Job: %s_%s" % (fid, cid)
        logging.warn(msg)
        return HttpResponseBadRequest('Fine', mimetype="text/plain")

    pandaid = request.POST.get('PandaID', None)
    info = request.POST.get('msg', None)

    if pandaid:
        send_mail('PANDAID found', 'PANDAID:%s, CID:%s'% (pandaid,j.cid), 'atl@py-dev.lancs.ac.uk', ['p.love@lancaster.ac.uk'], fail_silently=False)

        msg = "%s pandaid:%s, pilot status:%s" % (j.cid, pandaid, j.result)
        logging.warn(msg)

#        try:
#            p = Pandaid(pid=int(pandaid), job=j)
#            p.save()
#            msg = 'monpost: PandaID=%s' % pandaid
#            m = Message(job=j, msg=msg, client=request.META['REMOTE_ADDR'])
#            m.save()
#        except:
#            msg = "Problem creating Pandaid: %s" % pandaid
#            logging.warn(msg)
    else:
        l = len(request.POST.keys())
        msg = "no info from monpost(), post len:%s" % l
        m = Message(job=j, msg=msg, client=request.META['REMOTE_ADDR'])
        m.save()
        #if j.result != 20:
        msg = "%s monpost no pandaid, pilot status: %s, post len:%s" % (j.cid, j.result, l)
        logging.warn(msg)

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
            m = Message(job=j, msg=msg, client=request.META['REMOTE_ADDR'])
            m.save()
            msg = "%s -> FAULT (AWOL) FID:%s CID:%s" % (j.state, j.fid, j.cid)
            logging.warn(msg)
            j.state = State.objects.get(name='FAULT')
            j.flag = True
            j.save()

    return HttpResponse("OK", mimetype="text/plain")

def awolold(request):
    """
    Handle jobs which have been lost within condor
    """

    fid = request.POST.get('fid', None)
    cid = request.POST.get('cid', None)

    if not (fid and cid):
        content = "Bad request"
        return HttpResponseBadRequest(content, mimetype="text/plain")

    try:
        j = Job.objects.get(fid__name=fid, cid=cid)
    except Job.DoesNotExist:
        content = "DoesNotExist: %s" % cid
        return HttpResponseBadRequest(content, mimetype="text/plain")

    if j.state.name not in ['DONE', 'FAULT']:
        msg = "%s -> FAULT (AWOL)" % j.state
        m = Message(job=j, msg=msg, client=request.META['REMOTE_ADDR'])
        m.save()
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

    cstate = State.objects.get(name='CREATED')
    rstate = State.objects.get(name='RUNNING')
    estate = State.objects.get(name='EXITING')

    deltat = datetime.now() - timedelta(hours=24)
    cjobs = Job.objects.filter(fid=f, state=cstate, last_modified__lt=deltat)[:500]

    deltat = datetime.now() - timedelta(hours=48)
    rjobs = Job.objects.filter(fid__name=fid, state__name='RUNNING', last_modified__lt=deltat)[:500]

    deltat = datetime.now() - timedelta(hours=1)
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

    pqs = PandaQueue.objects.all()

    response = HttpResponse(mimetype='text/plain')

    writer = csv.writer(response, delimiter=' ', lineterminator='\n')
    result = []
    for q in pqs:
        result.append(q.id)

    writer.writerow(result)

    return response

#def pandaqueues(request):
#    """
#    Return list of active panda queues
#    """
#
#    sites = Site.objects.filter(tags__name__in=['analysis','production']).distinct()
#
#    queues = []
#    for site in sites:
#        qs = PandaQueue.objects.filter(site=site)
#        queues += qs
#
#    response = HttpResponse(mimetype='text/plain')
#
#    writer = csv.writer(response)
#    for q in queues:
#        writer.writerow([q.name])
#
#    return response

def pandasites(request):
    """
    Return list of active panda site names (siteid)
    """

    sites = Site.objects.filter(tags__name__in=['analysis','production']).distinct()

    queues = []
    for site in sites:
        qs = PandaQueue.objects.filter(site=site)
        queues += qs

    response = HttpResponse(mimetype='text/plain')

    writer = csv.writer(response)
    for q in queues:
        writer.writerow([q.pandasite])

    return response


import rrdtool
import StringIO
import shutil
import tempfile
def img(request, t, fid, qid):
    db = '/var/tmp/rrd/job-state-%s-%s.rrd' % (fid, qid)
    t = str(t)
    db = str(db)

    # serialize to HTTP response
    response = HttpResponse(mimetype="image/png")
    f = tempfile.NamedTemporaryFile(dir='/dev/shm')

    output = rrdtool.graph(f.name,
            '--title', 'Hello',
            '--watermark', 'x',
            '--start', 'end-%s' % t,
            '--lower-limit', '0',
            '--vertical-label', "number of jobs" 
#            'DEF:cr=%s:created:AVERAGE' % db,
            'DEF:cr=/var/tmp/rrd/job-state-1-1.rrd:created:AVERAGE',
            'DEF:rn=%s:running:AVERAGE' % db,
            'DEF:ex=%s:exiting:AVERAGE' % db,
            'DEF:ft=%s:fault:AVERAGE' % db,
            'DEF:dn=%s:done:AVERAGE' % db,
#            'CDEF:st1=cr,1,*',
            'CDEF:st2=rn,1,*',
            'CDEF:st3=ex,1,*',
            'CDEF:st4=ft,1,*',
            'CDEF:st5=dn,1,*',
            'CDEF:ln1=cr,cr,UNKN,IF',
            'CDEF:ln2=rn,cr,rn,+,UNKN,IF',
            'CDEF:ln3=ex,rn,cr,ex,+,+,UNKN,IF',
            'CDEF:ln4=ft',
            'CDEF:ln5=dn',
            'AREA:st1#ECD748:CREATED',
            'STACK:st2#48C4EC:RUNNING',
            'STACK:st3#EC9D48:EXITING',
            'LINE1:ln1#C9B215',
            'LINE1:ln2#1598C3',
            'LINE1:ln3#CC7016',
            'LINE3:ln4#cc3118:FAULT',
            'LINE3:ln5#23bc14:DONE',
            )

    shutil.copyfileobj(f, response)
    f.close()
    return response


def test(request):

    pandaqs = PandaQueue.objects.all()

    rows = []
    for pandaq in pandaqs:

        labs = []
        labels = Label.objects.filter(pandaq=pandaq)
        for lab in labels:
            labs.append(lab)
        nlabs = len(labs)

        serviced = 'pass'
        if nlabs == 1:
            serviced = 'warn'
        if nlabs == 0:
            serviced = 'fail'

        row = {
            'pandaq' : pandaq,
            'labs' : labs,
            'count' : len(labs),
            'serviced' : serviced,
            }
        rows.append(row)

    sortedrows = sorted(rows, key=itemgetter('count')) 
    context = {
        'rows' : sortedrows,
        }

    return render_to_response('mon/service.html', context)

def index(request):
    """
    Rendered view of front page
    """

    factories = Factory.objects.all().order_by('name')
   
    dtfail = datetime.now() - timedelta(hours=1)
    dtwarn = datetime.now() - timedelta(minutes=10)
    jobs = Job.objects.all()

    cstate = State.objects.get(name='CREATED')
    rstate = State.objects.get(name='RUNNING')
    estate = State.objects.get(name='EXITING')
    dstate = State.objects.get(name='DONE')
    fstate = State.objects.get(name='FAULT')

    rows = []
    for f in factories:

#        ncreated = jobs.filter(fid=f, state=cstate).count()
        ncreated = 0

        active = 'fail'
        if f.last_modified > dtfail:
            active = 'warn'
        if f.last_modified > dtwarn:
            active = 'pass'
        row = {
            'factory' : f,
            'active' : active,
            'ncreated' : ncreated,
            }

        rows.append(row)

    context = {
            'rows' : rows,
            'plot' : 'on',
            }

    return render_to_response('mon/index.html', context)

def testtimeline(request):

    jobs = Job.objects.filter(label__name='UKI-NORTHGRID-LANCS-HEP-abaddon-cream').order_by('-last_modified')

    context = {
            'jobs' : jobs[:10],
            }

    return render_to_response('mon/test.html', context)

def queues(request):
    """
    Rendered view of all queues, all factories.
    """

    pandaqs = PandaQueue.objects.all()
    dt = datetime.now() - timedelta(hours=1)
    jobs = Job.objects.all()

    cstate = State.objects.get(name='CREATED')
    rstate = State.objects.get(name='RUNNING')
    estate = State.objects.get(name='EXITING')
    dstate = State.objects.get(name='DONE')
    fstate = State.objects.get(name='FAULT')
    astates = [cstate, rstate, estate]

    rows = []
    for pandaq in pandaqs:
        labs = Label.objects.filter(pandaq=pandaq)
        nactive = 0
        ndone = 0
        nfault = 0
        nactive = jobs.filter(pandaq=pandaq, state__in=[cstate,rstate,estate]).count()
        ndone = jobs.filter(pandaq=pandaq, state=dstate, last_modified__gt=dt).count()
        nfault = jobs.filter(pandaq=pandaq, state=fstate, last_modified__gt=dt).count()

        statactive = 'hot'
        statdone = 'pass'
        if nactive <= 2000:
            statactive = 'pass'
        if nactive <= 5:
            statactive = 'cold'
#            if ndone <= 1:
#                statdone = 'cold'

        statfault = 'hot'
#        if nfault <= 12:
#            statfault = 'warn'
        if nfault <= 10:
            statfault = 'pass'

        activewarn = datetime.now() - timedelta(minutes=5)
        activeerror = datetime.now() - timedelta(minutes=10)
        activity = 'ok'
        for lab in labs:
            if activewarn > lab.last_modified:
                activity = 'warn'
            if activeerror > lab.last_modified:
                activity = 'note'
    
        row = {
            'pandaq' : pandaq,
            'nactive' : nactive,
            'ndone' : ndone,
            'nfault' : nfault,
            'statactive' : statactive,
            'statdone' : statdone,
            'statfault' : statfault,
            'activity' : activity,
            }

        rows.append(row)

    # factories with jobs in active states
    fids = Factory.objects.filter(job__state__in=astates).annotate(nactive=Count('job'))
        
    context = {
            'rows' : rows,
            'factories' : fids,
            'plot' : 'on',
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


    
    return HttpResponse("OK-shout", mimetype="text/plain")

def cr2(request):
    """
    Create the Job, expect data format is:
    (cid, nick, fid, label)
    """

    jdecode = json.JSONDecoder()

    raw = request.POST.get('data', None)
    
    if raw:
        try:
            data = jdecode.decode(raw)
            ncreated = len(data)
            msg = "Number of jobs in JSON data: %d" % ncreated
            logging.debug(msg)
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
    
            pq, created = PandaQueue.objects.get_or_create(name=nick)
            if created:
                msg = "PandaQueue auto-created: %s" % nick
                logging.warn(msg)
        
            ip = request.META['REMOTE_ADDR']
            f, created = Factory.objects.get_or_create(name=fid, defaults={'ip':ip})
            if created:
                msg = "Factory auto-created: %s" % fid
                logging.warn(msg)
            f.last_ncreated = ncreated
            f.save()
        
            l, created = Label.objects.get_or_create(name=label, fid=f, pandaq=pq)
            if created:
                msg = "Label auto-created: %s" % label
                logging.warn(msg)
        
            try:
                state = State.objects.get(name='CREATED')
                j = Job(cid=cid, fid=f, state=state, pandaq=pq, label=l)
                j.save()
            except Exception, e:
                msg = "Failed to create: %s_%s" % (f, cid)
                logging.error(msg)
                return HttpResponseBadRequest(msg, mimetype="text/plain")
        
            msg = "CREATED"
            m = Message(job=j, msg=msg, client=request.META['REMOTE_ADDR'])
            m.save()

    return HttpResponse("OK", mimetype="text/plain")

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
         'last_startup' : datetime.now(),
         'version' : ver,
        }

    f, created = Factory.objects.get_or_create(name=fid, defaults=d)
    if created:
        msg = "Factory auto-created: %s" % fid
        logging.info(msg)

    f.ip = ip
    f.url = url
    f.email = owner
    f.last_startup = datetime.now()
    f.version = ver
    f.save()

    return HttpResponse("OK", mimetype="text/plain")

def msg(request):
    """
    Update the latest factory messages. Expect data format:
    (nick, fid, label, text)
    """

    jdecode = json.JSONDecoder()

    cycle = request.POST.get('cycle', None)
    raw = request.POST.get('data', None)
    
    if raw:
        try:
            data = jdecode.decode(raw)
            msg = "Number of msgs in JSON data: %d" % len(data)
            logging.debug(msg)
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
        
            pq, created = PandaQueue.objects.get_or_create(name=nick)
            if created:
                msg = "PandaQueue auto-created: %s" % nick
                logging.warn(msg)
        
            ip = request.META['REMOTE_ADDR']
            f, created = Factory.objects.get_or_create(name=fid, defaults={'ip':ip})
            if created:
                msg = "Factory auto-created: %s" % fid
                logging.warn(msg)
            if cycle:
                f.last_cycle = cycle
            f.save()
        
            l, created = Label.objects.get_or_create(name=label, fid=f, pandaq=pq)
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

def info(request):

    context = {}
    return render_to_response('mon/info.html', context)


def search(request):
    """
    Search for a string in pandaqueue, sites, labels.
    """

    query = request.GET.get('q', '')

    # see Simple generic views in django docs

    url = reverse('atl.mon.views.query', args=(query,))
    logging.debug(url)
    return HttpResponseRedirect(url)

def query(request, q):
    """
    Search for a string in pandaq
    """
    if q:
        qset = (
            Q(pandaq__name__icontains=q)
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