from kit.models import Site
from kit.models import WMSQueue
from kit.models import BatchQueue

import csv
import logging
import socket
from datetime import timedelta, datetime
from django.utils.timezone import utc
from django.shortcuts import render_to_response, get_object_or_404
from django.db.models import Count
from django.db.models import Q
from django.http import HttpResponse, Http404, HttpResponseBadRequest

try:
    import json as json
except ImportError, err:
    import simplejson as json

def pandaqueues(request):
    """
    Return list of panda queues
    """

    qs = BatchQueue.objects.all()

    response = HttpResponse(content_type='text/plain')
    writer = csv.writer(response)
    for q in qs:
        writer.writerow([q.name])

    return response

def pandasites(request):
    """
    Return list of active panda site names (siteid/panda_site)
    """

    sites = Site.objects.filter(tags__name__in=['analysis','production']).distinct()

    queues = []
    for site in sites:
        qs = BatchQueue.objects.filter(wmsqueue__site=site)
        queues += qs

    response = HttpResponse(content_type='text/plain')

    writer = csv.writer(response)
    for q in queues:
        writer.writerow([q.wmsqueue])

    return response

def update(request):
    """
    Handle a POST contains json data from AGIS

    {
      "rc_site": "UKI-NORTHGRID-LANCS-HEP",
      "atlas_site": "UKI-NORTHGRID-LANCS-HEP",
      "cloud": "UK",
      "nickname": "UKI-NORTHGRID-LANCS-HEP-abaddon-normal-lsf",
      "panda_resource": "UKI-NORTHGRID-LANCS-HEP",
      "panda_site": "UKI-NORTHGRID-LANCS-HEP",
      "comment": "empty.comment",
      "status_control": "manual",
      "type": "PRODUCTION_QUEUE",
      "tier": "T2D",
      "last_modified": "2011-08-16 08:55:15"
    },
    """

    raw = None
    if request.method == 'POST':
        raw = request.body

    if not raw:
        content = "Bad request no data"
        logging.error(content)
        return HttpResponseBadRequest(content, content_type="text/plain")

    try:
        jdict = json.loads(raw)
        msg = "AGIS JSON entry count: %d" % len(jdict)
        logging.error(msg)
    except:
        raise
        msg = "Error decoding POST json data"
        logging.error(msg)
        content = "Bad request, failed to decode json"
        return HttpResponseBadRequest(content, content_type="text/plain")

    for pq in jdict.keys():
        d = jdict[pq]
        if not d: continue

        msg = 'Updating AGIS BatchQueue: %s' % pq
        logging.debug(msg)
        try:
            defaults = {'name' : d['rc_site'],
                        'gocdbname' : d['rc_site'],
                        'ssbname' : d['atlas_site'],
#                        'pandasitename' : d['panda_site'],
                        'cloud' : d['cloud'],
                        'tier' : d['tier'],
                        }
            site, created = Site.objects.get_or_create(name=d['rc_site'], defaults=defaults)
            if created:
                msg = "Site auto-created: %s" % site
                logging.warn(msg)
            
            defaults = {'name' : d['panda_resource'],
                        'site' : site,
                        }
            wmsqueue, created = WMSQueue.objects.get_or_create(name=d['panda_resource'], defaults=defaults)
            if created:
                msg = "WMSQueue auto-created: %s" % wmsqueue
                logging.warn(msg)
    
            defaults = {'name' : d['nickname'],
                        'wmsqueue' : wmsqueue,
                        }
            batchqueue, created = BatchQueue.objects.get_or_create(name=d['nickname'], defaults=defaults)
            if created:
                msg = "BatchQueue auto-created: %s" % batchqueue
                print msg
                logging.warn(msg)

        except Exception, e:
            msg = "Exception caught: %s" % e
            print msg
            logging.error(msg)

        # update key values
        try:
            if wmsqueue.site_id != site.id:
                wmsqueue.site = site
                wmsqueue.save()

            if batchqueue.wmsqueue_id != wmsqueue.id:
                batchqueue.wmsqueue = wmsqueue
                batchqueue.save()

            if batchqueue.comment != d['comment']:
                batchqueue.comment = d['comment'] 
                batchqueue.save()
    
            f = '%Y-%m-%dT%H:%M:%S.%f'
            dt = datetime.strptime(d['last_modified'], f).replace(tzinfo=utc)
            if batchqueue.timestamp != dt:
                batchqueue.timestamp = dt
                batchqueue.save()
    
            if batchqueue.state != d['status']:
                batchqueue.state = d['status']
                batchqueue.save()
    
            if batchqueue.type != d['type']:
                batchqueue.type = d['type']
                batchqueue.save()
    
            if batchqueue.control != d['status_control']:
                batchqueue.control = d['status_control']
                batchqueue.save()
        except Exception, e:
            msg = "Exception caught: %s" % e
            print msg
            logging.error(msg)

        content = 'updated %d' % len(jdict)
    return HttpResponse(content, content_type="text/plain")
