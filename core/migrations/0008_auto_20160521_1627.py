# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-05-21 16:27
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_auto_20160520_1720'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='order',
            options={'ordering': ['-created_on']},
        ),
    ]
