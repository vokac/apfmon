from django.db import models

"""
Model to represent the ATLAS topology of Sites and resources
"""

CLOUDS = (
        ('CA', 'CA'),
        ('CERN', 'CERN'),
        ('DE', 'DE'),
        ('ES', 'ES'),
        ('FR', 'FR'),
        ('IT', 'IT'),
        ('ND', 'ND'),
        ('NL', 'NL'),
        ('RU', 'RU'),
        ('TW', 'TW'),
        ('UK', 'UK'),
        ('US', 'US'),
        )

QTYPE = (
        ('ANALYSIS_QUEUE', 'ANALYSIS_QUEUE'),
        ('PRODUCTION_QUEUE', 'PRODUCTION_QUEUE'),
        ('SPECIAL_QUEUE', 'SPECIAL_QUEUE'),
        )

class Site(models.Model):
    """
    Represents a GOCDB/SSB/AGIS site, single sysadmin control
    """
    name = models.CharField(max_length=128, unique=True)
    gocdbname = models.CharField(max_length=128, unique=True, null=True)
    ssbname = models.CharField(max_length=128, null=True)
    cloud = models.CharField(max_length=8, choices=CLOUDS, blank=True, null=True)
    tier = models.CharField(max_length=8, blank=True, null=True)
    last_modified = models.DateTimeField(auto_now=True, editable=False, null=True)
    def __unicode__(self):
        return self.name
    class Meta:
        ordering = ['name']

class WMSQueue(models.Model):
    """
    Represents a Panda Site (siteid) 
    """
    name = models.CharField(max_length=64)
    site = models.ForeignKey(Site, blank=True, null=True, on_delete=models.CASCADE)
    def __unicode__(self):
        return self.name
    class Meta:
        ordering = ['name']

class BatchQueue(models.Model):
    """
    Represents a Panda queue (nickname)
    """
    name = models.CharField(max_length=64, unique=True)
    wmsqueue = models.ForeignKey(WMSQueue, blank=True, null=True, on_delete=models.CASCADE)
    state = models.CharField(max_length=16, blank=True, default='unknown')
    comment = models.CharField(max_length=140, blank=True, default='')
    type = models.CharField(max_length=32, choices=QTYPE, blank=True, null=True)
    control = models.CharField(max_length=32, blank=True, null=True)
    # this should be upstream timestamp. ie. from SSB json data
    timestamp = models.DateTimeField(editable=False, null=True)
    last_modified = models.DateTimeField(auto_now=True, editable=False, null=True)
    def __unicode__(self):
        return self.name
    class Meta:
        ordering = ['name']
