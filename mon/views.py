from mon.models import Factory
from mon.models import Job
from mon.models import Label
from mon.models import STATES

from kit.models import Site
from kit.models import BatchQueue
from kit.models import WMSQueue
from kit.models import CLOUDS

import csv
import logging
import math
import pytz
import re
import redis
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
from django.http import HttpResponseServerError
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.conf import settings
from django.core.mail import mail_managers
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.serializers.json import DjangoJSONEncoder
from django.core.urlresolvers import reverse
from django.core.exceptions import MultipleObjectsReturned
from django.utils.encoding import smart_text

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
NSUBMITTED = re.compile('ready=(\d+),.*ret=(\d+)$')
PENDING = re.compile('.*;MaxPending:in=(\d+),pend=(\d+),max=(\d+),ret=(\d+)$')
CLOUDLIST = []
for item in CLOUDS:
    CLOUDLIST.append(item[0])
STATELIST = []
for item in STATES:
    STATELIST.append(item[0])


red = redis.StrictRedis(settings.REDIS['host'] , port=settings.REDIS['port'], db=0)
expire2days = 172800
expire5days = 432000
expire7days = 604800
expire3hrs = 3*3600
span = 7200
interval = 300

# Flows
# 1. CREATED <- condor_id (Entry)
# 3. RUNNING <- signal from pilot-wrapper
# 4. EXITING <- signal from pilot-wrapper
# 5. DONE <- signal from cronjob script (mon-expire.py) jobstate=4

def humanmsg(rawmsg):
    """
    Translate the factory schedconfig message into something understandable by sysadmins
    """
    nret = 0
    nready = 0
    nmatch = NSUBMITTED.match(rawmsg)
    if nmatch:
        nready = int(nmatch.group(1))
        nret = int(nmatch.group(2))

    inpending = 0
    npending = 0
    maxpending = 0
    pending = PENDING.match(rawmsg)
    if pending:
        inpending = int(pending.group(1))
        npending = int(pending.group(2))
        maxpending = int(pending.group(3))
        nret = int(pending.group(4))

    if nret == 0:
        if nready == 0:
            reason = '0 pilots submitted, no work available'
        else:
            if inpending  > 0:
                if npending == maxpending:
                    reason = '0 pilots submitted, %d pilots already pending' % npending

            else: 
                reason = '0 pilots submitted, check raw messages'

        return reason
        
    if nret == 1:
        reason = '%d pilot submitted' % nret
    else:
        reason = '%d pilots submitted' % nret
    return reason

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

    key = ':'.join(('joblog',job.jid))
    msglist = red.lrange(key, 0, -1)

    msgs = []
    for msg in msglist:
        # msg is a string with format:
        # "<epoch_time> <client_ip> <some message with spaces>"
        (t, ip, txt) = msg.split(' ',2)
        msg = {'received' : datetime.fromtimestamp(float(t), pytz.utc),
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

    dir = str(job.label.name).translate(string.maketrans('/:','__'))

    outurl = out % (f.url, date, dir, job.cid)
    errurl = err % (f.url, date, dir, job.cid)
    logurl = log % (f.url, date, dir, job.cid)

    
    context = {
                'outurl'  : outurl,
                'errurl'  : errurl,
                'logurl'  : logurl,
                'factory' : f,
                'job'     : job,
                'msgs'    : msgs,
                'clouds' : CLOUDLIST,
                }

    return render_to_response('mon/job.html', context)

@cache_page(60 * 1)
def factory(request, fid):
    """
    Rendered view of Factory instance. Lists all factory labels with
    a count of jobs in each state.
    """

    try:
        id = int(fid)
    except ValueError:
        raise Http404

    dtdead = datetime.now(pytz.utc) - timedelta(days=10)

    f = get_object_or_404(Factory, id=id)
    labels = Label.objects.filter(fid=f, last_modified__gt=dtdead).values('name','last_modified')

    key = ':'.join(('ringf',f.name))

    context = {
            'labels'     : labels,
            'factory'  : f,
            'activity' : getactivity(key),
            'clouds' : CLOUDLIST,
            }

    return render_to_response('mon/factory.html', context)

#@cache_page(60 * 3)
def pandaq(request, qid, p=1):
    """
    Rendered view of panda queue for all factories
    qid can now be batchqueue name or id
    """

    if not qid:
        msg = 'Bad request, BatchQueue missing.'
        return HttpResponseBadRequest(msg, content_type="text/plain")

    q = get_object_or_404(BatchQueue, name=qid)

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

        dtwarn = datetime.now(pytz.utc) - timedelta(minutes=15)
        dtstale = datetime.now(pytz.utc) - timedelta(minutes=60)

        active = 'stale'
        if lab.last_modified > dtstale:
            active = 'warn'
        if lab.last_modified > dtwarn:
            active = 'pass'

        row['activity'] = active
        row['reason'] = humanmsg(lab.msg)

        rows.append(row)

    pages = Paginator(Job.objects.filter(label__batchqueue=q).order_by('-last_modified'), 100)
    jobs = Job.objects.filter(label__batchqueue=q).order_by('-last_modified')[:100]

    context = {
            'pandaq' : q,
            'rows' : rows,
            'jobs' : jobs,
            'pages' : pages,
            'page' : pages.page(p),
            'clouds' : CLOUDLIST,
            }

    return render_to_response('mon/pandaq.html', context)

def offline(request):

    context = {}
    return render_to_response('mon/offline.html', context)

# APIv1
@cache_page(60 * 30)
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
            val = Job.objects.filter(label=l, state='done').count()
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
            val = Job.objects.filter(label=l, state='fault').count()
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
        nhit = Job.objects.filter(state='done', label=l, result=0).count()
        nmiss = Job.objects.filter(state='done', label=l, result=20).count()

        if l.batchqueue:
            bqname = l.batchqueue.name 
            bqid = l.batchqueue.id 
        else:
            bqname = ""
            bqid = ""

        row = {
            'label'      : l.name,
            'labelid'    : l.id,
            'factory'    : l.fid.name,
            'factoryid'  : l.fid.id,
            'factoryver' : l.fid.version,
            'resource'   : l.resource,
            'pandaq'     : bqname,
            'pandaqid'   : bqid,
            'ndone'      : ndone,
            'nfault'     : nfault,
            'nhit'       : nhit,
            'nmiss'      : nmiss,
            'logurl'     : logurl,
            'timestamp'  : datetime.now(pytz.utc).strftime('%F %H:%M:%S UTC'),
            }
        rows.append(row)

    context = {
        'rows' : rows,
        }

    return HttpResponse(json.dumps(rows, sort_keys=True, indent=2), mimetype="application/json")

# UI
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

            # dull messages
            cssclass = pandaq.state 
#            if pandaq.type in ['SPECIAL_QUEUE']:
#                cssclass = 'muted'

            dull = [
                    'HC.Blacklist.set.online',
                    'HC.Blacklist.set.test',
                    ]
            msgclass = cssclass
            if pandaq.comment in dull:
                msgclass = 'muted'

            row = {
                    'site'     : site,
                    'url'      : url,
                    'prefix'   : prefix,
                    'suffix'   : suffix,
                    'pandaq'   : pandaq,
                    'class'    : cssclass,
                    'msgclass' : msgclass,
                    }
            rows.append(row)

    context = {
            'factive' : factive,
            'finactive' : finactive,
            'cloud' : name,
            'sites' : sites,
            'rows' : rows,
            'clouds' : CLOUDLIST,
            }


    return render_to_response('mon/cloud.html', context)

def testtimeline(request):

    jobs = Job.objects.filter(label__name='UKI-NORTHGRID-LANCS-HEP-abaddon-cream').order_by('-last_modified')

    context = {
            'jobs' : jobs[:10],
            }

    return render_to_response('mon/test.html', context)

# UI wtf
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

# UI
def help(request):

    context = {
            'clouds' : CLOUDLIST,
            }
    return render_to_response('mon/help.html', context)

def search(request):
    """
    Handle search form
    """

    query = request.GET.get('q', '')

    # see Simple generic views in django docs

    # smart_text to ensure unicode
    url = reverse('apfmon.mon.views.query', args=(smart_text(query),))
    logging.debug(url)
    return HttpResponseRedirect(url)

# UI
def query(request, q=None):
    """
    Search for a string in batchqueue, wmsqueue, site
    """
    if q:
        result = red.lpush('apfmon:query', q)
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
        'clouds' : CLOUDLIST,
    }
    return render_to_response('mon/query.html', context)

# UI
def site(request, sid):
    """
    Rendered view of Site page showing table of Pandaqs for this Site
    including stats from all factories
    Note: this is a Site not a PandaSite

    sid can now be the sitename as well as the siteID
    """

    try:
        sint = int(sid)
        s = get_object_or_404(Site, id=sint)
    except ValueError:
        s = get_object_or_404(Site, name=sid)
        

    dt = datetime.now(pytz.utc) - timedelta(days=7)

    # all labels serving this site
    labels = Label.objects.filter(batchqueue__wmsqueue__site=s)
    labels = labels.filter(last_modified__gt=dt)

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
        row['reason'] = humanmsg(label.msg)
        rows.append(row)

    context = {
            'site' : s,
            'rows' : rows,
            'clouds' : CLOUDLIST,
            }


    return render_to_response('mon/site.html', context)

# UI
#@cache_page(60 * 10)
def report(request):
    """
    Render a report of suspicious queues
    """

    # redis, how bout using sorted sets with a score based on number of fault?
    dt = datetime.now(pytz.utc) - timedelta(minutes=120)
    labels = Label.objects.filter(last_modified__gt=dt)
    results = []
    foo = []
    for label in labels:
        jobs = Job.objects.filter(label=label)
        created = jobs.filter(state='created', created__gt=dt).count()
        if created < 100: continue
        fault = jobs.filter(state='fault').count()
        if fault <= 100: continue
        done = jobs.filter(state='done').count()
        total = done+fault
        if total:
            per = int(100*fault/total)
        else:
            per = 0

        if per < 90: continue

        # redis tallies
        key = ':'.join(('fault', label.fid.name, label.name))
        rfault = red.scard(key)
        key = ':'.join(('done', label.fid.name, label.name))
        rdone = red.scard(key)
        rtotal = rdone+rfault
        if rtotal:
            rper = int(100*rfault/rtotal)
        else:
            rper = 0
        result = {
            'id'      : label.id,
            'name'    : label.name,
            'factory' : label.fid.name,
            'fid'     : label.fid.id,
            'total'   : total,
            'created' : created,
            'done'    : done,
            'fault'   : fault,
            'per'     : per,
            'rfault'  : rfault,
        }
        results.append(result)

    foo = sorted(results, key=itemgetter('per', 'created'), reverse=True)
    

    context = {
#        'rows'     : sortedrows[:20],
#        'sololist' : sololist,
#        'orphans'  : orphans,
#        'hotlabels'   : hot,
        'results'     : foo,
        'clouds' : CLOUDLIST,
        }

    if request.META.get('HTTP_ACCEPT','') == 'application/json':
        return HttpResponse(json.dumps(foo, sort_keys=True, indent=2), mimetype="application/json")
    else:
        return render_to_response('mon/report.html', context)

# UI
def singletest(request, fname, item):
    """
    Rendered view of a single item, either label or job
    """

    try:
        label = Label.objects.get(name=item)
        lid = ':'.join((label.fid.name,label.name))

        context = {
            'label' : '/api/labels/%s' % lid
            }
        return render_to_response('mon/singlelabel.html', context)
    except:
        pass

    try:
        job = Job.objects.get(fid=fname, cid=item)
    except:
        # return 404, neither label or job found
        pass

    
    # make an ordered jobcount list from the redis hash
    labelkey = ':'.join(('ringl',lid))

    key = ':'.join(('status',lab.fid.name,lab.name))
    msgs = red.lrange(key, 0, -1)
    print key, msgs
    context = {
            'label'    : lab,
            'lid'      : lid,
            'jobs'     : jobs,
            'pages'    : pages,
            'page'     : pages.page(p),
            'status'   : status,
            'activity' : getactivity(labelkey),
            'msgs'     : msgs,
            'counts'   : counts,
            'clouds' : CLOUDLIST,
            }

    return render_to_response('mon/label.html', context)

# UI
def singlefactory(request, fname):
    """
    Rendered view of a single Label or Job
    """
    f = get_object_or_404(Factory, name=fname)

    return factory(request, f.id)

# UI
def singleitem(request, fname, item):
    """
    Rendered view of a single Label or Job
    """

    try:
        lab = Label.objects.get(fid__name=fname,name=item)
        state = request.GET.get('state', None)
        return label(request, lab.id, state)

    except Label.DoesNotExist:
        # continue and try to get a Job
        pass

    jid = ':'.join((fname, item))
    try:
        job = Job.objects.get(jid=jid)

        return job1(request, job.label.fid.id, job.cid)
    except Job.DoesNotExist:
        msg = 'Neither label or job found: %s %s' % (fname, item)
        logging.warn(msg)
        raise Http404

# UI
def label(request, lid, state=None):
    """
    Rendered view of a single Label with job details
    """

    lab = get_object_or_404(Label, id=lid)

    dt = datetime.now(pytz.utc) - timedelta(hours=1)
    # factories with labels serving selected pandaq

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
    ndone = jobs.filter(state='done').count()
    nfault = jobs.filter(state='fault').count()
    nmiss = jobs.filter(state='done', result=20).count()
    total = jobs.count()
    
    counts = {
            'created' : ncreated,
            'running' : nrunning,
            'exiting' : nexiting,
            'done'    : ndone,
            'fault'   : nfault,
            'miss'    : nmiss,
            'total'   : total,
            }

    activewarn = datetime.now(pytz.utc) - timedelta(minutes=10)
    activeerror = datetime.now(pytz.utc) - timedelta(minutes=30)
    status = ''
    if activewarn > lab.last_modified:
        status = 'text-warning'
    if activeerror > lab.last_modified:
        status = 'text-error'

    if state in STATELIST:
        jobs = Job.objects.filter(label=lab, state=state).order_by('-last_modified')[:100]
    else:
        jobs = Job.objects.filter(label=lab).order_by('-last_modified')[:100]
    
    # make an ordered jobcount list from the redis hash
    lid = ':'.join((lab.fid.name,lab.name))
    labelkey = ':'.join(('ringl',lid))

    key = ':'.join(('status',lab.fid.name,lab.name))
    msglist = red.lrange(key, 0, -1)
    msglist.reverse()

    msgs = []
    for msg in msglist:
        # msg is a string with format:
        # "<epoch_time> <client_ip> <some message with spaces>"
        (t, ip, txt) = msg.split(' ',2)
        msg = {'received' : datetime.fromtimestamp(float(t), pytz.utc),
               'client'   : ip,
               'msg'      : txt,
             }

#        statuslist = txt.split(';')
#        if statuslist:
#            endchunk = statuslist[-1]
#            msg['msg'] = endchunk

        msgs.append(msg)

    if msgs:
        lastmsg = msgs[0]
    else:
        lastmsg = {'received' : lab.last_modified,
                   'client'   : '',
                   'msg'      : lab.msg,
                 }

    reason = humanmsg(lastmsg['msg'])


    context = {
            'label'    : lab,
            'lid'      : lid,
            'jobs'     : jobs,
#            'pages'    : pages,
#            'page'     : pages.page(p),
            'status'   : status,
            'lastmsg'  : lastmsg,
            'activity' : getactivity(labelkey),
            'msgs'     : msgs,
            'counts'   : counts,
            'clouds'   : CLOUDLIST,
            'state'    : state,
            'reason'   : reason,
            }

    return render_to_response('mon/label.html', context)

def getactivity(key):
    """
    Helper function to massage the redis activity output. Takes a
    redis hash key and returns a list of integers.
    """
    n = span / interval
    buckets = []
    for i in range(n):
        t = time.time() - (i * interval)
        buckets.append(math.floor((t % span) / interval))
    activity = red.hmget(key, buckets)
    def makezero(value): return int(0 if value is None else value)
    activity = map(makezero, activity)
    activity.reverse()
    

    return activity[2:]

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

def testindex(request):
    """
    Rendered view of front page which shows a table of activity
    for each factories
    """
    dtfail = datetime.now(pytz.utc) - timedelta(days=10)
    dterror = datetime.now(pytz.utc) - timedelta(hours=1)
    dtwarn = datetime.now(pytz.utc) - timedelta(minutes=20)

    factories = Factory.objects.all().order_by('name')

    rows = []
    activities = []
    for f in factories:
        if f.last_modified < dtfail: continue

        # this 'active' string map to a html classes
        active = 'text-error'
        if f.last_modified > dterror:
            active = 'text-warning'
        if f.last_modified > dtwarn:
            active = ''

        key = ':'.join(('ringf',f.name))
        buckets = getactivity(key)
        activities.append(buckets)
        lastbucket = buckets[-1]

        row = {
            'factory'    : f,
            'active'     : active,
            'lastbucket' : lastbucket,
            }

        rows.append(row)

    status = red.get('apfmon:status')

    context = {
            'rows' : rows,
            'acts'   : activities,
            'clouds' : CLOUDLIST,
            'status' : status,
            }

    return render_to_response('mon/index.html', context)


@cache_page(60 * 1)
def index(request):
    """
    Rendered view of front page which shows a table of activity
    for each factories
    """
    dtfail = datetime.now(pytz.utc) - timedelta(days=10)
    dterror = datetime.now(pytz.utc) - timedelta(hours=1)
    dtwarn = datetime.now(pytz.utc) - timedelta(minutes=20)

    factories = Factory.objects.all().order_by('name')

    rows = []
    activities = []
    for f in factories:
        if f.last_modified < dtfail: continue

        # this 'active' string map to a html classes
        active = 'text-error'
        if f.last_modified > dterror:
            active = 'text-warning'
        if f.last_modified > dtwarn:
            active = ''

        key = ':'.join(('ringf',f.name))
        buckets = getactivity(key)
        activities.append(buckets)
        lastbucket = buckets[-1]

        row = {
            'factory'    : f,
            'active'     : active,
            'lastbucket' : lastbucket,
            }

        rows.append(row)

    status = red.get('apfmon:status')

    context = {
            'rows' : rows,
            'acts'   : activities,
            'clouds' : CLOUDLIST,
            'status' : status,
            }

    return render_to_response('mon/index.html', context)

def test500(request):
    """
    Return a server error http response 500
    """
    msg = 'HttpResponse (not 500)'
    return HttpResponse(msg, content_type="text/plain")
#    msg = 'HttpResponseServerError (500)'
#    return HttpResponseServerError(msg, content_type="text/plain")

