from apfmon.mon.models import Factory
from apfmon.mon.models import Job
from apfmon.mon.models import Label

from apfmon.kit.models import Site
from apfmon.kit.models import BatchQueue
from apfmon.kit.models import WMSQueue

import json
import logging
import math
import pytz
import redis
import statsd
import time
from datetime import timedelta, datetime
from django.shortcuts import redirect, render_to_response, get_object_or_404
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.conf import settings
from django.core.cache import cache
#from django.views.decorators.cache import cache_page
from django.core.mail import mail_managers
from django.core.serializers.json import DjangoJSONEncoder
from django.core.urlresolvers import reverse
from django.core.exceptions import MultipleObjectsReturned


ss = statsd.StatsClient(settings.GRAPHITE['host'], settings.GRAPHITE['port'])
red = redis.StrictRedis(settings.REDIS['host'] , port=settings.REDIS['port'], db=0)
expire2days = 172800
expire5days = 432000
expire7days = 604800
expire3hrs = 3*3600
span = 7200
interval = 300

def job(request, id):
    """
    Handle requests from /jobs/{id} resource

    GET:
    Return a specific job including list of messages

    POST:
    Update the Job using data in the querystring
    state : either 'running' or 'exiting'
    ids   : comma separated list of pandaids (not implemented)
    """

    ip = request.META['REMOTE_ADDR']

    try:
        job = Job.objects.get(jid=id)
    except Job.DoesNotExist:
        response = HttpResponse(mimetype="text/plain", status=404)
        location = "/api/jobs/%s" % id
        response['Location'] = location
        msg = "Not found: " + request.build_absolute_uri(location)
        response.write(msg)
        return response
        

    if request.method == 'GET':

        msglist = red.lrange(job.jid, 0, -1)

        jobfields = ('jid', 'cid', 'created', 'flag',
                   'label__name', 'label__fid__name', 'last_modified',
                   'result', 'state')
        j = Job.objects.filter(jid=id).values(*jobfields)[0]

        j['messages'] = msglist
        j['factory'] = j['label__fid__name']
        del j['label__fid__name']
        j['label'] = j['label__name']
        del j['label__name']


        response = HttpResponse(json.dumps(j, 
                                cls=DjangoJSONEncoder,
                                sort_keys=True,
                                indent=2),
                                mimetype="application/json")
        location = "/api/jobs/%s" % job.jid
        response['Location'] = location
        return response
        

    if request.method == 'POST':
        newstate = request.POST.get('state', None)
        rc = request.POST.get('rc', None)
        joblog = ':'.join(('joblog',job.jid))

        if newstate == 'running':
            if job.state != 'created':
                msg = "Invalid state transition, %s->%s" % (
                                                job.state, newstate)
                element = "%f %s %s" % (time.time(),
                                        request.META['REMOTE_ADDR'],
                                        msg)
                red.rpush(joblog, element)
                return HttpResponseBadRequest(msg, mimetype="text/plain")

            job.state = 'running'
            job.save()
            msg = "State change: created->running"
            element = "%f %s %s" % (time.time(),
                                    request.META['REMOTE_ADDR'],
                                    msg)
            red.rpush(joblog, element)
            red.expire(joblog, expire5days)
            response = HttpResponse(mimetype="text/plain")
            location = "/api/jobs/%s" % job.jid
            response['Location'] = location
            msg = request.build_absolute_uri(location)
            response.write(msg)
            return response

        elif newstate == 'exiting':
            if job.state != 'running':
                msg = "Invalid state transition: %s->%s" % (
                                                job.state, newstate)
                element = "%f %s %s" % (time.time(),
                                        request.META['REMOTE_ADDR'],
                                        msg)
                red.rpush(joblog, element)
                return HttpResponseBadRequest(msg, mimetype="text/plain")

            job.state = 'exiting'
            if rc: job.result = rc
            job.save()
            msg = "State change: running->exiting (pilot return code: %s)" % rc
            element = "%f %s %s" % (time.time(),
                                    request.META['REMOTE_ADDR'],
                                    msg)
            red.rpush(joblog, element)
            red.expire(joblog, expire2days)
            location = "/api/jobs/%s" % job.jid
            msg = request.build_absolute_uri(location)
            return HttpResponse(msg, mimetype="text/plain")

        else:
            msg = "Invalid data: %s" % dict(request.POST)
            return HttpResponseBadRequest(msg, mimetype="text/plain")

    if request.method == 'DELETE':
        if ip == '127.0.0.1':
            job.delete()
            return HttpResponse(mimetype="text/plain")
        else: 
            context = "Remote deletion is forbidden"
            return HttpResponseForbidden(context, mimetype="text/plain")
            

    context = 'HTTP method not supported: %s' % request.method
    return HttpResponse(context, mimetype="text/plain")

def jobs(request):
    """
    Handle requests from /jobs resource.

    GET:
    Return a list of jobs refined by zero or more URL parameters fid,state,label

    PUT:
    Create the Job, expect data format is a JSON encoded list of dicts
    with the following keys:
    cid     : unique id of job, usually condorid but can be anything 
    factory : factory name
    label   : factory label for each queue (name of section in factory config)

    The label must already exist and usually created at factory (re)start.
    """

    ip = request.META['REMOTE_ADDR']
    if 'CONTENT_LENGTH' in request.META.keys():
        length = request.META['CONTENT_LENGTH']
        msg = "APIv2 content length: %s" % length
        logging.debug(msg)
        ss.gauge('apfmon.length.apijobs', length)
    else:
        msg = 'No CONTENT_LENGTH in request'
        logging.debug(msg)


    if request.method == 'PUT':

        msg = "RAW REQUEST: %s %s %s" % (request.method, ip, request.body)
        logging.debug(msg)

        try:
            jobs = json.loads(request.body)
        except ValueError, e:
            msg = str(e)
            return HttpResponseBadRequest(msg, mimetype="text/plain")

        msg = "API number of jobs in JSON data: %d (%s)" % (len(jobs), ip)
        logging.debug(msg)

        nfailed = 0
        ncreated = 0
        for job in jobs:
            factory = job['factory']
            label = job['label']
            cid = job['cid']
            
            f = Factory.objects.get(name=factory)

            try: 
                lab = Label.objects.get(name=label, fid=f)
            except MultipleObjectsReturned,e:
                msg = "Multiple objects - apfv2 issue?"
                logging.warn(msg)
                msg = "Multiple objects error"
                return HttpResponseBadRequest(msg, mimetype="text/plain")
            except Label.DoesNotExist:
                msg = "Label not found: %s, job %s:%s" % (label, factory, cid)
                logging.warn(msg)
                nfailed += 1
                continue
    
            # this awesome section populates a ring-counter with the number
            # of jobs per label over the last 2hrs with 5 min buckets
            # giving 24 buckets
            # two ring counters 'ringl', 'ringf'
            labelkey = ':'.join(('ringl',f.name,lab.name))
            factorykey = ':'.join(('ringf',f.name))
            bucket = '%s' % math.floor((time.time() % span) / interval)
            next1bucket = '%s' % math.floor(((time.time()+interval) % span) / interval)
            next2bucket = '%s' % math.floor(((time.time()+(2*interval)) % span) / interval)
            pipe = red.pipeline()
            pipe.hincrby(labelkey, bucket, 1)
            pipe.hincrby(factorykey, bucket, 1)
            pipe.hmset(labelkey, {next1bucket:0, next2bucket:0})
            pipe.hmset(factorykey, {next1bucket:0, next2bucket:0})
            pipe.expire(labelkey, expire3hrs)
            pipe.expire(factorykey, expire3hrs)
            pipe.execute()
            
            jid = ':'.join((f.name,cid))
            j = Job(jid=jid, cid=cid, state='created', label=lab)
            j.save()
            ncreated += 1

        f = Factory.objects.get(name=factory)
        f.last_ncreated = ncreated
        f.save()
        txt = 'job' if len(jobs) == 1 else 'jobs'
        context = 'Created %d/%d %s, %d not created' % (ncreated, len(jobs), txt, nfailed)
        status = 201 if ncreated else 200
        return HttpResponse(context, status=status, mimetype="text/plain")

    if request.method == 'GET':
        jobs = Job.objects.all()
        factory = request.GET.get('factory', None)
        label = request.GET.get('label', None)
        site = request.GET.get('site', None)
        state = request.GET.get('state', None)
        offset = request.GET.get('offset', 0)
        limit = request.GET.get('limit', 50)
        order = request.GET.get('order','last_modified')

        if factory:
            jobs = jobs.filter(label__fid__name=factory)

        if label:
            jobs = jobs.filter(label__name=label)

        if state:
            jobs = jobs.filter(state=state.lower())

        jobs.order_by(order)
        offset = max(0,int(offset))
        limit = int(limit)
        start = min(offset, jobs.count())
        end = min(offset+limit, jobs.count())
        if limit == 0:
            jobs = jobs[start:]
        else:
            jobs = jobs[start:end]

        fields = ('jid','state','created','last_modified','result','flag')
        return HttpResponse(json.dumps(list(jobs.values(*fields)), 
                            cls=DjangoJSONEncoder,
                            sort_keys=True,
                            indent=2),
                            mimetype="application/json")

    context = 'HTTP method not supported: %s' % request.method
    return HttpResponse(context, status=405, mimetype="text/plain")

def label(request, id=None):
    """
    Handle requests for the /labels/{id} resource 

    GET:
    Return a label identified by {id} where id = factory:labelname

    POST:
    status : message from factory updating status of [queue]
           : truncated to 140 chars

    DELETE:
    Delete a Label, restricted to localhost
    """

    ip = request.META['REMOTE_ADDR']
    if 'CONTENT_LENGTH' in request.META.keys():
        length = request.META['CONTENT_LENGTH']
        msg = "APIv2 content length: %s" % length
        logging.debug(msg)
        ss.gauge('apfmon.length.apilabel', length)
    else:
        msg = 'No CONTENT_LENGTH in request'
        logging.debug(msg)

    try:
        factory, name = id.split(':')
    except ValueError:
        msg = "Invalid %s request" % request.method
        return HttpResponseBadRequest(msg, mimetype="text/plain")
        
    label = get_object_or_404(Label, name=name, fid__name=factory)

    if request.method == 'GET':
        fields = ('id','name','fid__name','msg','created','last_modified','resource','localqueue')

        lab = Label.objects.filter(name=name, fid__name=factory).values(*fields)[0]
        lab['factory'] = lab['fid__name']
        del lab['fid__name']
        truth = ['unsub', 'pend', 'stgin', 'running', 'stgout', 'held']
        for t in truth:
            lab[t] = '-'

        key = ':'.join(('ringl',lab['factory'],lab['name']))
        n = span / interval
        buckets = []
        for i in range(n):
            t = time.time() - (i * interval)
            buckets.append(math.floor((t % span) / interval))

        lab['activity'] = getactivity(key)

        return HttpResponse(json.dumps(lab,
                            cls=DjangoJSONEncoder,
                            sort_keys=True,
                            indent=2),
                            mimetype="application/json")

    if request.method == 'POST':
        status = request.POST.get('status', None)
        if not status:
            msg = "Invalid data: %s" % dict(request.POST)
            return HttpResponseBadRequest(msg, mimetype="text/plain")

        # still hitting DB here, to be removed
        label.msg = status[:140]
        label.save()
        # have 1024 chars for fullmsg coming from sched plugins
        # but only write to redis
        fullmsg = status[:1024]
        content = "%f %s %s" % (time.time(),
                                request.META['REMOTE_ADDR'],
                                fullmsg)

        key = ':'.join(('status',label.fid.name,label.name))
        pipe = red.pipeline()
        pipe.rpush(key, content)
        pipe.expire(key, expire5days)
        pipe.ltrim(key,-5,-1)
        pipe.execute()


        response = HttpResponse(mimetype="text/plain")
        location = "/api/labels/%s" % ':'.join((factory,name))
        response['Location'] = location
        return response

    if request.method == 'DELETE':
        if ip == '127.0.0.1':
            label = get_object_or_404(Label, name=name, fid__name=factory)
            label.delete()
            return HttpResponse(mimetype="text/plain")
        else: 
            context = "Remote deletion is forbidden"
            return HttpResponseForbidden(context, mimetype="text/plain")

    context = "HTTP method not supported: %s" % request.method
    return HttpResponse(context, status=405, mimetype="text/plain")


def labels(request):
    """
    Handle requests for the /labels resource 

    GET:
    Return a list of all labels

    PUT:
    Create or update a collection of Labels. Accepts a JSON encoded list of qcl
    """

    ip = request.META['REMOTE_ADDR']

    if 'CONTENT_LENGTH' in request.META.keys():
        length = request.META['CONTENT_LENGTH']
        msg = "APIv2 content length: %s" % length
        logging.debug(msg)
        ss.gauge('apfmon.length.apilabels', length)
    else:
        msg = 'No CONTENT_LENGTH in request'
        logging.debug(msg)

    if request.method == 'PUT':

        msg = "RAW REQUEST: %s %s %s" % (request.method, ip, request.body)
        logging.debug(msg)

        try:
            data = json.loads(request.body)
        except ValueError, e:
            msg = str(e)
            return HttpResponseBadRequest(msg, mimetype="text/plain")

        msg = "Number of json objects PUT /api/labels: %d (%s)" % (len(data), ip)
        logging.debug(msg)

        nupdated = 0
        ncreated = 0
        for d in data:
            logging.debug(d)
            
            try:
                name = d['name']
                factory = d['factory']
            except KeyError, e:
                msg = "KeyError in label: %s" % str(e)
                logging.warn(msg)
                continue

            batchqueue = d.get('batchqueue', None)
            resource = d.get('resource', None)
            localqueue = d.get('localqueue', None)

            try:
                f = Factory.objects.get(name=factory)
            except Factory.DoesNotExist:
                msg = "Factory not found: %s" % factory
                logging.warn(msg)
                continue
                
            try: 
                label, created = Label.objects.get_or_create(name=name, fid=f)
            except:
                msg = "Exception get_or_create /api/labels: %s, fid: %s" % (name,f)
                logging.error(msg)
                continue
                
            if created:
                msg = "Label auto-created: %s" % label.name
                logging.warn(msg)
                ncreated += 1
            else:
                nupdated += 1

            if batchqueue:
                bq, created = BatchQueue.objects.get_or_create(name=batchqueue)
                if bq != label.batchqueue:
                    label.batchqueue = bq
            
            if resource and resource != label.resource:
                label.resource = resource 
            if localqueue and localqueue != label.localqueue:
                label.localqueue = localqueue 
            label.save()

        txt = 'label' if len(data) == 1 else 'labels'
        context = 'Created %d/%d %s, %d updated' % (ncreated, len(data), txt, nupdated)
        status = 201 if ncreated else 200
        return HttpResponse(context, status=status, mimetype="text/plain")

    if request.method == 'GET':
        labels = Label.objects.all()

        factory = request.GET.get('factory', None)
        name = request.GET.get('name', None)
        batchqueue = request.GET.get('batchqueue', None)
        offset = request.GET.get('offset', 0)
        limit = request.GET.get('limit', 50)
        order = request.GET.get('order','name')
        
        if factory:
            labels = labels.filter(fid__name=factory)
        if name:
            jobs = jobs.filter(name=name)
        if batchqueue:
            jobs = jobs.filter(batchqueue=batchqueue)

        labels.order_by(order)
        offset = max(0,int(offset))
        limit = int(limit)
        start = min(offset, labels.count())
        end = min(offset+limit, labels.count())
        if limit == 0:
            labels = labels[start:]
        else:
            labels = labels[start:end]

        fields = ('id','name','batchqueue__name','fid__name','msg','last_modified','resource')

        data = list(labels.values(*fields))

    
        for d in data:
            # make an ordered jobcount list from the redis hash
            
            jobs = Job.objects.filter(label=d['id'])
            d['ncreated'] = jobs.filter(state='created').count()
            d['nrunning'] = jobs.filter(state='running').count()
            d['nexiting'] = jobs.filter(state='exiting').count()
            d['ndone'] =    jobs.filter(state='done').count()
            d['nfault'] =   jobs.filter(state='fault').count()
            d['factory'] = d['fid__name']
            d['pandaq'] = d['batchqueue__name']
            del d['batchqueue__name']
            del d['fid__name']

            key = ':'.join(('lring',d['factory'],d['name']))
            n = span / interval
            buckets = []
            for i in range(n):
                t = time.time() - (i * interval)
                buckets.append(math.floor((t % span) / interval))

            d['activity'] = getactivity(key)
            
        return HttpResponse(json.dumps(data,
                            cls=DjangoJSONEncoder,
                            sort_keys=True,
                            indent=2),
                            mimetype="application/json")

    context = 'HTTP method not supported: %s' % request.method
    return HttpResponse(context, status=405, mimetype="text/plain")

def factory(request, id):
    """
    Handle requests to /factories/{id} resource.

    GET:
    Return a factory and list of labels associated with the factory.

    PUT:
    Create or update factory arrtributes, intended to be called upon
    factory start-up. Accepts one or more of the following parameters:
        + name
        + email
        + url
        + version

    DELETE:
    Delete a factory, restricted to localhost
    """

    # check for valid chars [\w-_]

    ip = request.META['REMOTE_ADDR']
    if 'CONTENT_LENGTH' in request.META.keys():
        length = request.META['CONTENT_LENGTH']
        msg = "APIv2 content length: %s" % length
        logging.debug(msg)
        ss.gauge('apfmon.length.apifactory', length)
    else:
        msg = 'No CONTENT_LENGTH in request'
        logging.debug(msg)

    dt = datetime.now(pytz.utc) - timedelta(days=10)

    if request.method == 'GET':
        f = get_object_or_404(Factory, name=id)

        fields = ('id', 'name', 'email', 'url', 'version', 'last_modified',
                  'last_startup', 'ip')
        f = Factory.objects.filter(name=id).values(*fields)[0]

        return HttpResponse(json.dumps(f, 
                            cls=DjangoJSONEncoder,
                            sort_keys=True,
                            indent=2),
                            mimetype="application/json")

    if request.method == 'PUT':
        msg = "RAW REQUEST: %s %s %s" % (request.method, ip, request.body)
        logging.debug(msg)

        data = json.loads(request.body)

        defaults = {
                'email'   : data.get('email', 'unknown@example.com'),
                'url'     : data.get('url', 'http://localhost/'),
                'version' : data.get('version', 'unknown'),
                'ip'      : ip,
                }

        if data.has_key('type'):
            defaults['factory_type'] = data['type']
                
        try:
            f, created = Factory.objects.get_or_create(name=id,
                                                       defaults=defaults)
        except:
            content = "Unable to create resource using: %s" % data
            return HttpResponseBadRequest(content, mimetype="text/plain")

        status = 201 if created else 200

        if data.has_key('type'):
            if f.factory_type != data['type']:
                f.factory_type = data['type']
                f.save()

        if f.email != data['email']:
            f.email = data['email']
            f.save() 

        if f.url != data['url']:
            f.url = data['url']
            f.save() 

        if f.version != data['version']:
            f.version = data['version']
            f.save() 

        if f.ip != ip:
            f.ip = ip
            f.save() 

        if created:
            mail_managers('Factory created: %s' % id,
                      'Factory created: %s' % id,
                      fail_silently=False)

        f.last_startup = datetime.now(pytz.utc)
        f.save()

        f = Factory.objects.filter(name=id).values()

        return HttpResponse(json.dumps(list(f), 
                            cls=DjangoJSONEncoder,
                            sort_keys=True,
                            indent=2),
                            status=status,
                            mimetype="application/json")

    if request.method == 'DELETE':
        if ip == '127.0.0.1':
            f = get_object_or_404(Factory, name=id)
            f.delete()
            return HttpResponse(mimetype="text/plain")
        else: 
            context = "Remote deletion is forbidden"
            return HttpResponseForbidden(context, mimetype="text/plain")

    context = 'HTTP method not supported: %s' % request.method
    return HttpResponse(context, mimetype="text/plain")

def factories(request):
    """
    Handle requests from /factories resource.

    GET:
    Return a list of all factories

    """

    ip = request.META['REMOTE_ADDR']

    if request.method != 'GET':
        context = 'HTTP method not supported: %s' % request.method
        return HttpResponse(context, mimetype="text/plain")

    dtactive = datetime.now(pytz.utc) - timedelta(days=10)

    fields = ('id', 'name', 'email', 'url', 'version', 'last_modified',
              'last_startup')
    factories = Factory.objects.values(*fields).order_by('name')

    for f in factories:
        active = True if f['last_modified'] > dtactive else False
        f['active'] = active

        key = ':'.join(('fring',f['name']))
        f['activity'] = getactivity(key)

        

    return HttpResponse(json.dumps(list(factories), 
                        cls=DjangoJSONEncoder,
                        sort_keys=True,
                        indent=2),
                        mimetype="application/json")

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

    return activity

