# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-09-20 19:20
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('referrals', '0006_auto_20170720_1609'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='referral',
            unique_together=set([('ip', 'code')]),
        ),
    ]
