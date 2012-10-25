from atl.kit.models import Cloud
from atl.kit.models import Tag
from atl.kit.models import Site
from atl.kit.models import PandaSite
from atl.kit.models import PandaQueue

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

    qs = PandaQueue.objects.all()

    response = HttpResponse(mimetype='text/plain')
    writer = csv.writer(response)
    for q in qs:
        writer.writerow([q.name])

    return response

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

def update(request):
    """
    Handle a POST contains json data from AGIS

  {
    "agis_gocdb_or_oim_site_name": "UKI-NORTHGRID-LANCS-HEP",
    "agis_ssb_site_name": "UKI-NORTHGRID-LANCS-HEP",
    "cloud": "UK",
    "ddm_site_name": "UKI-NORTHGRID-LANCS-HEP",
    "panda_queue": "UKI-NORTHGRID-LANCS-HEP-abaddon-normal-lsf",
    "panda_siteID": "UKI-NORTHGRID-LANCS-HEP",
    "panda_site_name": "UKI-NORTHGRID-LANCS-HEP",
    "queue_comment": "empty.comment",
    "queue_status_control": "manual",
    "queue_type": "PRODUCTION_QUEUE",
    "tier": "T2D",
    "timestamp": "2011-08-16 08:55:15"
  },

    """

    raw = request.POST.get('data', None)

    if not raw:
        content = "Bad request"
        return HttpResponseBadRequest(content, mimetype="text/plain")

#    return HttpResponse("OK", mimetype="text/plain")
    jdecode = json.JSONDecoder()
    try:
        data = jdecode.decode(raw)
        msg = "JSON SSB length: %d" % len(data)
        print msg
        logging.debug(msg)
    except:
        msg = "Error decoding POST json data"
        print msg
        logging.error(msg)
        content = "Bad request, failed to decode json"
        return HttpResponseBadRequest(content, mimetype="text/plain")

#    return HttpResponse("OK", mimetype="text/plain")
    for d in data:
        if not d: continue

        try:
            cloud, created = Cloud.objects.get_or_create(name=d['cloud'])
            if created:
                msg = "Cloud auto-created: %s" % cloud
                print msg
                logging.warn(msg)
                
            defaults = {'name' : d['agis_gocdb_or_oim_site_name'],
                        'gocdbname' : d['agis_gocdb_or_oim_site_name'],
                        'ssbname' : d['agis_ssb_site_name'],
                        'pandasitename' : d['panda_site_name'],
                        'cloud' : cloud,
                        }
            site, created = Site.objects.get_or_create(name=d['agis_gocdb_or_oim_site_name'], defaults=defaults)
            if created:
                msg = "Site auto-created: %s" % site
                print msg
                logging.warn(msg)
            
            defaults = {'name' : d['panda_siteID'],
                        'site' : site,
                        'tier' : d['tier'],
                        }
            pandasite, created = PandaSite.objects.get_or_create(name=d['panda_siteID'], defaults=defaults)
            if created:
                msg = "PandaSite auto-created: %s" % site
                print msg
                logging.warn(msg)
    
    
            defaults = {'name' : d['panda_queue'],
                        'pandasite' : pandasite,
                        }
            pandaq, created = PandaQueue.objects.get_or_create(name=d['panda_queue'], defaults=defaults)
            if created:
                msg = "PandaQueue auto-created: %s" % site
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

#            print pandaq.comment,d['queue_comment']
            if pandaq.comment != d['queue_comment']:
                pandaq.comment = d['queue_comment'] 
                pandaq.save()
    
#            print pandaq.timestamp,d['timestamp']
            f = '%Y-%m-%d %H:%M:%S'
            dt = datetime.strptime(d['timestamp'], f).replace(tzinfo=utc)
            if pandaq.timestamp != dt:
                pandaq.timestamp = dt
                pandaq.save()
    
#            print pandaq.state,d['queue_status']
            if pandaq.state != d['queue_status']:
                pandaq.state = d['queue_status']
                pandaq.save()
    
#            print pandaq.type, d['queue_type']
            if pandaq.type != d['queue_type']:
                pandaq.type = d['queue_type']
                pandaq.save()
    
#            print pandaq.control, d['queue_status_control']
            if pandaq.control != d['queue_status_control']:
                pandaq.control = d['queue_status_control']
                pandaq.save()
        except Exception, e:
            msg = "Exception caught: %s" % e
            print msg
            logging.error(msg)


    return HttpResponse("OK", mimetype="text/plain")
