# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-04-24 10:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0047_merge_20180316_1223'),
    ]

    operations = [
        migrations.AddField(
            model_name='currency',
            name='property_id',
            field=models.IntegerField(blank=True, max_length=3, null=True, unique=True),
        ),
    ]