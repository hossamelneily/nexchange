# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-08 12:56
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ticker', '0012_pair_disabled'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='price',
            name='price_eur',
        ),
        migrations.RemoveField(
            model_name='price',
            name='price_rub',
        ),
        migrations.RemoveField(
            model_name='price',
            name='price_usd',
        ),
        migrations.RemoveField(
            model_name='price',
            name='rate_eur',
        ),
        migrations.RemoveField(
            model_name='price',
            name='rate_usd',
        ),
        migrations.RemoveField(
            model_name='price',
            name='type',
        ),
    ]