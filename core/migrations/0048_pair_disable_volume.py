# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-04-26 14:43
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0047_merge_20180316_1223'),
    ]

    operations = [
        migrations.AddField(
            model_name='pair',
            name='disable_volume',
            field=models.BooleanField(default=False, help_text='Opt-out this Pair on Volume endpoint.'),
        ),
    ]