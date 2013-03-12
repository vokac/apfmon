from atl.kit.models import Cloud
from atl.kit.models import Tag
from atl.kit.models import Site
from atl.kit.models import PandaSite
from atl.kit.models import BatchQueue

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

    response = HttpResponse(mimetype='text/plain')
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
        qs = BatchQueue.objects.filter(site=site)
        queues += qs

    response = HttpResponse(mimetype='text/plain')

    writer = csv.writer(response)
    for q in queues:
        writer.writerow([q.pandasite])

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
        return HttpResponseBadRequest(content, mimetype="text/plain")

    try:
        jdict = json.loads(raw)
        msg = "AGIS JSON entry count: %d" % len(jdict)
        logging.error(msg)
    except:
        raise
        msg = "Error decoding POST json data"
        logging.error(msg)
        content = "Bad request, failed to decode json"
        return HttpResponseBadRequest(content, mimetype="text/plain")

    for pq in jdict.keys():
        d = jdict[pq]
        if not d: continue

        msg = 'Updating AGIS BatchQueue: %s' % pq
        logging.debug(msg)
        try:
            cloud, created = Cloud.objects.get_or_create(name=d['cloud'])
            if created:
                msg = "Cloud auto-created: %s" % cloud
                logging.warn(msg)
                
            defaults = {'name' : d['rc_site'],
                        'gocdbname' : d['rc_site'],
                        'ssbname' : d['atlas_site'],
                        'pandasitename' : d['panda_site'],
                        'cloud' : cloud,
                        }
            site, created = Site.objects.get_or_create(name=d['rc_site'], defaults=defaults)
            if created:
                msg = "Site auto-created: %s" % site
                logging.warn(msg)
            
            defaults = {'name' : d['panda_resource'],
                        'site' : site,
                        'tier' : d['tier'],
                        }
            pandasite, created = PandaSite.objects.get_or_create(name=d['panda_resource'], defaults=defaults)
            if created:
                msg = "PandaSite auto-created: %s" % site
                logging.warn(msg)
    
            defaults = {'name' : d['nickname'],
                        'pandasite' : pandasite,
                        }
            pandaq, created = BatchQueue.objects.get_or_create(name=d['nickname'], defaults=defaults)
            if created:
                msg = "BatchQueue auto-created: %s" % pandaq
                print msg
                logging.warn(msg)

        except Exception, e:
            msg = "Exception caught: %s" % e
            print msg
            logging.error(msg)

        # update key values
        try:
            if pandaq.pandasite_id == None:
                pandaq.pandasite = pandasite
                pandaq.save()

#            print pandaq.comment,d['comment']
            if pandaq.comment != d['comment']:
                pandaq.comment = d['comment'] 
                pandaq.save()
    
#            print pandaq.timestamp,d['last_modified']
            f = '%Y-%m-%dT%H:%M:%S.%f'
            dt = datetime.strptime(d['last_modified'], f).replace(tzinfo=utc)
            if pandaq.timestamp != dt:
                pandaq.timestamp = dt
                pandaq.save()
    
#            print pandaq.state,d['status']
            if pandaq.state != d['status']:
                pandaq.state = d['status']
                pandaq.save()
    
#            print pandaq.type, d['type']
            if pandaq.type != d['type']:
                pandaq.type = d['type']
                pandaq.save()
    
#            print pandaq.control, d['status_control']
            if pandaq.control != d['status_control']:
                pandaq.control = d['status_control']
                pandaq.save()
        except Exception, e:
            msg = "Exception caught: %s" % e
            print msg
            logging.error(msg)

        content = 'updated %d' % len(jdict)
    return HttpResponse(content, mimetype="text/plain")
