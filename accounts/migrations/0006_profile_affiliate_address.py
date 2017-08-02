# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-04-18 15:47
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_merge_20170406_1558'),
        ('accounts', '0005_auto_20170415_0934'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='affiliate_address',
            field=models.ForeignKey(
                default=None,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='core.Address'),
        ),
    ]
