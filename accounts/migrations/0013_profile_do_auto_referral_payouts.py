# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-03-20 13:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_auto_20170712_1906'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='do_auto_referral_payouts',
            field=models.BooleanField(default=False),
        ),
    ]