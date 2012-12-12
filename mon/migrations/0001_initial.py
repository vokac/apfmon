# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'State'
        db.create_table('mon_state', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(default='CREATED', max_length=16)),
        ))
        db.send_create_signal('mon', ['State'])

        # Adding model 'Factory'
        db.create_table('mon_factory', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64, blank=True)),
            ('ip', self.gf('django.db.models.fields.IPAddressField')(max_length=15, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, blank=True)),
            ('url', self.gf('django.db.models.fields.URLField')(default='', max_length=200, blank=True)),
            ('version', self.gf('django.db.models.fields.CharField')(max_length=64, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('last_startup', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('last_cycle', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('last_ncreated', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=0)),
        ))
        db.send_create_signal('mon', ['Factory'])

        # Adding model 'Label'
        db.create_table('mon_label', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64, blank=True)),
            ('fid', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mon.Factory'])),
            ('pandaq', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['kit.PandaQueue'])),
            ('msg', self.gf('django.db.models.fields.CharField')(max_length=140, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('mon', ['Label'])

        # Adding model 'Job'
        db.create_table('mon_job', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, db_index=True, blank=True)),
            ('cid', self.gf('django.db.models.fields.CharField')(max_length=16)),
            ('fid', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mon.Factory'])),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, db_index=True, blank=True)),
            ('state', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mon.State'])),
            ('pandaq', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['kit.PandaQueue'])),
            ('label', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mon.Label'])),
            ('result', self.gf('django.db.models.fields.SmallIntegerField')(default=-1, blank=True)),
            ('flag', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('mon', ['Job'])

        # Adding unique constraint on 'Job', fields ['fid', 'cid']
        db.create_unique('mon_job', ['fid_id', 'cid'])

        # Adding model 'Message'
        db.create_table('mon_message', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('job', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mon.Job'])),
            ('received', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, db_index=True, blank=True)),
            ('msg', self.gf('django.db.models.fields.CharField')(max_length=140, blank=True)),
            ('client', self.gf('django.db.models.fields.IPAddressField')(max_length=15)),
        ))
        db.send_create_signal('mon', ['Message'])


    def backwards(self, orm):
        # Removing unique constraint on 'Job', fields ['fid', 'cid']
        db.delete_unique('mon_job', ['fid_id', 'cid'])

        # Deleting model 'State'
        db.delete_table('mon_state')

        # Deleting model 'Factory'
        db.delete_table('mon_factory')

        # Deleting model 'Label'
        db.delete_table('mon_label')

        # Deleting model 'Job'
        db.delete_table('mon_job')

        # Deleting model 'Message'
        db.delete_table('mon_message')


    models = {
        'kit.cloud': {
            'Meta': {'ordering': "['name']", 'object_name': 'Cloud'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '8', 'blank': 'True'})
        },
        'kit.pandaqueue': {
            'Meta': {'ordering': "['name']", 'object_name': 'PandaQueue'},
            'comment': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            'control': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'}),
            'pandasite': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['kit.PandaSite']", 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'unknown'", 'max_length': '16', 'blank': 'True'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['kit.Tag']", 'symmetrical': 'False', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'})
        },
        'kit.pandasite': {
            'Meta': {'ordering': "['name']", 'object_name': 'PandaSite'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['kit.Site']", 'null': 'True', 'blank': 'True'}),
            'tier': ('django.db.models.fields.CharField', [], {'max_length': '8', 'null': 'True', 'blank': 'True'})
        },
        'kit.site': {
            'Meta': {'ordering': "['name']", 'object_name': 'Site'},
            'cloud': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['kit.Cloud']", 'null': 'True', 'blank': 'True'}),
            'gocdbname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'pandasitename': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            'ssbname': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['kit.Tag']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'kit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'})
        },
        'mon.factory': {
            'Meta': {'object_name': 'Factory'},
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'blank': 'True'}),
            'last_cycle': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'last_ncreated': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'last_startup': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'mon.job': {
            'Meta': {'ordering': "('-last_modified',)", 'unique_together': "(('fid', 'cid'),)", 'object_name': 'Job'},
            'cid': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'fid': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mon.Factory']"}),
            'flag': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mon.Label']"}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'pandaq': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['kit.PandaQueue']"}),
            'result': ('django.db.models.fields.SmallIntegerField', [], {'default': '-1', 'blank': 'True'}),
            'state': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mon.State']"})
        },
        'mon.label': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Label'},
            'fid': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mon.Factory']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'msg': ('django.db.models.fields.CharField', [], {'max_length': '140', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'pandaq': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['kit.PandaQueue']"})
        },
        'mon.message': {
            'Meta': {'object_name': 'Message'},
            'client': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mon.Job']"}),
            'msg': ('django.db.models.fields.CharField', [], {'max_length': '140', 'blank': 'True'}),
            'received': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'})
        },
        'mon.state': {
            'Meta': {'object_name': 'State'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "'CREATED'", 'max_length': '16'})
        }
    }

    complete_apps = ['mon']