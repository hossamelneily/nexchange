# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-29 23:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0011_auto_20170124_2149'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='moderator_flag',
            field=models.IntegerField(default=None,
                                      null=True, blank=True),
        ),
    ]