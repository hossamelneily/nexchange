# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-10-24 10:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('risk_management', '0003_account_trading_allowed'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='is_main_account',
            field=models.BooleanField(default=False),
        ),
    ]
