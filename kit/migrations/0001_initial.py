# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Cloud'
        db.create_table('kit_cloud', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=8, blank=True)),
        ))
        db.send_create_signal('kit', ['Cloud'])

        # Adding model 'Tag'
        db.create_table('kit_tag', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=40)),
        ))
        db.send_create_signal('kit', ['Tag'])

        # Adding model 'Site'
        db.create_table('kit_site', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128)),
            ('gocdbname', self.gf('django.db.models.fields.CharField')(max_length=128, unique=True, null=True)),
            ('ssbname', self.gf('django.db.models.fields.CharField')(max_length=128, null=True)),
            ('pandasitename', self.gf('django.db.models.fields.CharField')(max_length=128, null=True)),
            ('cloud', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['kit.Cloud'], null=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
        ))
        db.send_create_signal('kit', ['Site'])

        # Adding M2M table for field tags on 'Site'
        db.create_table('kit_site_tags', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('site', models.ForeignKey(orm['kit.site'], null=False)),
            ('tag', models.ForeignKey(orm['kit.tag'], null=False))
        ))
        db.create_unique('kit_site_tags', ['site_id', 'tag_id'])

        # Adding model 'PandaSite'
        db.create_table('kit_pandasite', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['kit.Site'], null=True, blank=True)),
            ('tier', self.gf('django.db.models.fields.CharField')(max_length=8, null=True, blank=True)),
        ))
        db.send_create_signal('kit', ['PandaSite'])

        # Adding model 'PandaQueue'
        db.create_table('kit_pandaqueue', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=64)),
            ('pandasite', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['kit.PandaSite'], null=True, blank=True)),
            ('state', self.gf('django.db.models.fields.CharField')(default='unknown', max_length=16, blank=True)),
            ('comment', self.gf('django.db.models.fields.CharField')(default='', max_length=140, blank=True)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('control', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
        ))
        db.send_create_signal('kit', ['PandaQueue'])

        # Adding M2M table for field tags on 'PandaQueue'
        db.create_table('kit_pandaqueue_tags', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('pandaqueue', models.ForeignKey(orm['kit.pandaqueue'], null=False)),
            ('tag', models.ForeignKey(orm['kit.tag'], null=False))
        ))
        db.create_unique('kit_pandaqueue_tags', ['pandaqueue_id', 'tag_id'])


    def backwards(self, orm):
        # Deleting model 'Cloud'
        db.delete_table('kit_cloud')

        # Deleting model 'Tag'
        db.delete_table('kit_tag')

        # Deleting model 'Site'
        db.delete_table('kit_site')

        # Removing M2M table for field tags on 'Site'
        db.delete_table('kit_site_tags')

        # Deleting model 'PandaSite'
        db.delete_table('kit_pandasite')

        # Deleting model 'PandaQueue'
        db.delete_table('kit_pandaqueue')

        # Removing M2M table for field tags on 'PandaQueue'
        db.delete_table('kit_pandaqueue_tags')


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
        }
    }

    complete_apps = ['kit']