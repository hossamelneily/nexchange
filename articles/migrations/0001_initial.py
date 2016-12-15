# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-12-15 22:14
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CmsPage',
            fields=[
                ('id',
                 models.AutoField(
                     auto_created=True,
                     primary_key=True,
                     serialize=False,
                     verbose_name='ID')),
                ('name',
                 models.CharField(
                     choices=[
                         ('about_us',
                          'about_us'),
                         ('careers',
                          'careers'),
                         ('press',
                          'press'),
                         ('conference',
                          'conference'),
                         ('legal_privacy',
                          'legal_privacy'),
                         ('security',
                          'security'),
                         ('faq',
                          'faq'),
                         ('blog',
                          'blog'),
                         ('fees',
                          'fees'),
                         ('support',
                          'support'),
                         ('trading_guide',
                          'trading_guide')],
                     default=None,
                     max_length=50)),
                ('head',
                 models.TextField(
                     default=None,
                     null=True)),
                ('written_by',
                 models.TextField(
                     default=None,
                     null=True)),
                ('body',
                 models.TextField(
                     default=None,
                     null=True)),
                ('locale',
                 models.CharField(
                     choices=[
                         ('ru',
                          'Russian'),
                         ('en',
                          'English'),
                         ('es',
                          'Espanol')],
                     default=(
                         'ru',
                         'Russian'),
                     max_length=2,
                     null=True)),
            ],
        ),
    ]
