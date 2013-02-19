from django.db import models
from atl.kit.models import PandaQueue

# Pilotjob STATE
# 
# States:
# 1. CREATED <- condor_id (Entry)
# 2. RUNNING <- signal from pilot wrapper
# 3. EXITING <- signal from pilot wrapper
# 4. DONE <- signal from mon-exiting Completed (jobstates=4)
# 5. FAULT <- signal from mon-exiting or mon-stale cron jobs (bad condor states)

# http://condor-wiki.cs.wisc.edu/index.cgi/wiki?p=MagicNumbers

# Condor globusstate:
#  1   PENDING The job is waiting for resources to become available to run.
#  2   ACTIVE  The job has received resources and the application is executing.
#  4   FAILED  The job terminated before completion because an error, user-triggered cancel, or system-triggered cancel.
#  8   DONE    The job completed successfully
#  16  SUSPENDED   The job has been suspended. Resources which were allocated for this job may have been released due to some scheduler-specific reason.
#  32  UNSUBMITTED The job has not been submitted to the scheduler yet, pending the reception of the GLOBUS_GRAM_PROTOCOL_JOB_SIGNAL_COMMIT_REQUEST signal from a client.
#  64  STAGE_IN    The job manager is staging in files to run the job.
#  128 STAGE_OUT   The job manager is staging out files generated by the job.
#  0xFFFFF     ALL     A mask of all job states. 

#  JobStatus in job ClassAds
#  0   Unexpanded  U
#  1   Idle    I
#  2   Running     R
#  3   Removed     X
#  4   Completed   C
#  5   Held    H
#  6   Submission_err  E
#  


#idea: how about a flat schema for jobs? Containing all related info without joins

JOBSTATES = (
            ('s', 'Submitted'),
            ('0', 'Unexpanded'),
            ('1', 'Idle'),
            ('2', 'Running'),
            ('3', 'Removed'),
            ('4', 'Completed'),
            ('5', 'Held'),
            ('6', 'Submission_err'),
        )

STATES = (
        ('CREATED', 'CREATED'),
        ('RUNNING', 'RUNNING'),
        ('EXITING', 'EXITING'),
        ('DONE', 'DONE'),
        ('FAULT', 'FAULT'),
        )

# this provides the base URL pointing to pilot logs
# todo: set this automatically by sending factory config
# to webservice when factory starts up
DEFAULTURL = ''

class State(models.Model):
    """
    Current state of job
    """
    name = models.CharField(max_length=16, choices=STATES, default='CREATED')
    def __unicode__(self):
        return str(self.get_name_display())

class Factory(models.Model):
    """
    Represent a factory instance
    """
    name = models.CharField(max_length=64, blank=True)
    ip = models.IPAddressField(blank=True)
    email = models.EmailField(blank=True)
    url = models.URLField(blank=True, verify_exists=False, default=DEFAULTURL)
    version = models.CharField(max_length=64, blank=True)
    last_modified = models.DateTimeField(auto_now=True, editable=False)
    last_startup = models.DateTimeField(editable=True, null=True)
    last_cycle = models.PositiveIntegerField(default=0)
    last_ncreated = models.PositiveSmallIntegerField(default=0)
    def __unicode__(self):
        return self.name

class Label(models.Model):
    """
    Represents a factory queue
    """
    name = models.CharField(max_length=64, blank=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    fid = models.ForeignKey(Factory)
    pandaq = models.ForeignKey(PandaQueue)
    msg = models.CharField(max_length=140, blank=True)
    last_modified = models.DateTimeField(auto_now=True, editable=False)
    queue = models.CharField(max_length=128, blank=True)
    localqueue = models.CharField(max_length=32, blank=True)
    def __unicode__(self):
        return self.name
    class Meta:
        get_latest_by = 'last_modified'
        ordering = ('name',)
        unique_together = ('fid', 'name',)

class Job(models.Model):
    """
    Represent a condor pilot job
    """
    jid = models.CharField(max_length=64, blank=False, unique=True)
    created = models.DateTimeField(auto_now_add=True, editable=False, db_index=True)
    cid = models.CharField(max_length=16, unique=False, blank=False)
    fid = models.ForeignKey(Factory)
    last_modified = models.DateTimeField(auto_now=True, editable=False, db_index=True)
    state = models.ForeignKey(State)
    pandaq = models.ForeignKey(PandaQueue, db_index=True)
    label = models.ForeignKey(Label)
    result = models.SmallIntegerField(blank=True, default=-1)
    flag = models.BooleanField(default=False)
    class Meta:
        ordering = ('-last_modified', )
    def __unicode__(self):
        return str(self.jid)
        
#class Pandaid(models.Model):
#    """
#    Simple many-to-one pandaid->job
#    """
#    pid = models.IntegerField(unique=False, blank=True, null=True)
#    job = models.ForeignKey(Job)
#    def __unicode__(self):
#        return str(self.pid)

class Message(models.Model):
    """
    Record messages like state changes
    """
    job = models.ForeignKey(Job, editable=False)
    received = models.DateTimeField(auto_now_add=True, editable=False, db_index=True)
    msg = models.CharField(max_length=140, blank=True)
    client = models.IPAddressField(editable=False)
    class Meta:
        get_latest_by = 'received'
    def __unicode__(self):
        return str(self.msg[:23])

#class StateHistory(models.Model):
#    """
#    (not used)
#    Record timestamp of each state change
#    """
#    job = models.ForeignKey(Job)
#    state_changed = models.DateTimeField(auto_now_add=True, editable=False)
#    from_state = models.ForeignKey(State, related_name='from_state')
#    to_state = models.ForeignKey(State , related_name='to_state')
