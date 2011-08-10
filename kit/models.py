from django.db import models

"""
Model to represent the ATLAS topology of Sites and resources
"""

CLOUDS = (
        ('UK', 'UK'),
        )

class Cloud(models.Model):
    """
    Represents an ATLAS cloud
    """
    name = models.CharField(max_length=8, choices=CLOUDS, blank=True, unique=True)
    def __unicode__(self):
        return self.name
    class Meta:
        ordering = ['name']

class Tag(models.Model):
    """
    tag string, used to select subset of sites
    """
    name = models.CharField(max_length=40)
    def __unicode__(self):
        return self.name

class Site(models.Model):
    """
    Represents a GOCDB Site 
    """
    name = models.CharField(max_length=128, unique=True)
    cloud = models.ForeignKey(Cloud, blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True)
    gocid = models.PositiveIntegerField(blank=True, null=True)
    last_modified = models.DateTimeField(auto_now=True, editable=False, null=True)
    def __unicode__(self):
        return self.name
    class Meta:
        ordering = ['name']

class PandaSite(models.Model):
    """
    Represents a Panda Site (siteid) 
    """
    name = models.CharField(max_length=64, unique=True)
    site = models.ForeignKey(Site, blank=True, null=True)
    state = models.CharField(max_length=16, blank=True, default='offline')
    tags = models.ManyToManyField(Tag, blank=True)
    def __unicode__(self):
        return self.name
    class Meta:
        ordering = ['name']

class PandaQueue(models.Model):
    """
    Represents a Panda queue 
    """
    name = models.CharField(max_length=64, unique=True)
    site = models.ForeignKey(Site, blank=True, null=True)
    pandasite = models.CharField(max_length=128, blank=True)
#    pandasite = models.ForeignKey(PandaSite, blank=True, null=True)
    state = models.CharField(max_length=16, blank=True, default='offline')
    tags = models.ManyToManyField(Tag, blank=True)
    def __unicode__(self):
        return self.name
    class Meta:
        ordering = ['name']

class Queue(models.Model):
    """
    Represent a CE resource hostname:queue
    """
    name = models.CharField(max_length=255, unique=True, blank=True)
    pandaq = models.ForeignKey(PandaQueue)
    tags = models.ManyToManyField(Tag, blank=True)
    def __unicode__(self):
        return self.name
    class Meta:
        ordering = ['id']

class Comment(models.Model):
    """
    Human editable notes
    """
    site = models.ForeignKey(Site)
    received = models.DateTimeField(auto_now_add=True, editable=False)
    msg = models.CharField(max_length=140, blank=True)
    dn = models.CharField(max_length=128, blank=True, editable=False)
    client = models.IPAddressField(blank=True, editable=False, default='127.0.0.1')
    class Meta:
        get_latest_by = 'received'
    def __unicode__(self):
        return str(self.msg[:23]+'...')
