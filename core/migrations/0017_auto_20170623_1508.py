# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-06-23 15:08
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_auto_20170607_1407'),
    ]

    operations = [
        migrations.AlterField(
            model_name='currency',
            name='ticker',
            field=models.CharField(
                blank=True,
                default=None,
                max_length=20,
                null=True),
        ),
    ]
