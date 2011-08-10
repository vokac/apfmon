from atl.kit.models import Tag
from atl.kit.models import Site
from atl.kit.models import PandaQueue
from atl.kit.models import Queue
from atl.kit.models import Comment

import csv
import logging
from datetime import timedelta, datetime
from django.shortcuts import render_to_response, get_object_or_404
from django.db.models import Count
from django.db.models import Q
from django.http import HttpResponse, Http404, HttpResponseBadRequest

def index(request):
    """
    Rendered view of front mon page
    """

    sites = Site.objects.all()
    pqs = PandaQueue.objects.all()
    analytag = Tag.objects.get(name='analysis')
    prodtag = Tag.objects.get(name='production')
    
    context = {
            'pqs' : pqs,
            'sites' : sites,
            }

    return render_to_response('kit/index.html', context)

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

