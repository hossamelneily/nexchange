# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-05-23 18:37
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_auto_20160522_0407'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='order',
            options={'ordering': ['-created_on']},
        ),
    ]