# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-27 15:22
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_auto_20170118_0042'),
    ]

    operations = [
        migrations.AddField(
            model_name='address',
            name='currency',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Currency'),
        ),
    ]
