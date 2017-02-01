# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-01-31 12:47
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_auto_20170129_0117'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='duplicate_of',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.Profile'),
        ),
    ]