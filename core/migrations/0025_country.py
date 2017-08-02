# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-07-27 07:43
from __future__ import unicode_literals

from django.db import migrations, models
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_currency_minimal_amount'),
    ]

    operations = [
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id',
                 models.AutoField(
                     auto_created=True,
                     primary_key=True,
                     serialize=False,
                     verbose_name='ID')),
                ('country',
                 django_countries.fields.CountryField(
                     max_length=2,
                     unique=True)),
            ],
        ),
    ]
