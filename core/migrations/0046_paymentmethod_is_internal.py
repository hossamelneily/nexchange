# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-09-17 16:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0045_auto_20160916_1119'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentmethod',
            name='is_internal',
            field=models.BooleanField(default=False),
        ),
    ]
