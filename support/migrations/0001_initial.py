# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-02-20 01:31
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('orders', '0002_auto_20170220_0130'),
    ]

    operations = [
        migrations.CreateModel(
            name='Support',
            fields=[
                ('id',
                 models.AutoField(
                     auto_created=True,
                     primary_key=True,
                     serialize=False,
                     verbose_name='ID')),
                ('name',
                 models.CharField(
                     max_length=50,
                     verbose_name='Name*')),
                ('email',
                 models.EmailField(
                     max_length=254,
                     verbose_name='Email*')),
                ('telephone',
                 models.CharField(
                     blank=True,
                     max_length=50,
                     null=True,
                     verbose_name='Telephone')),
                ('subject',
                 models.CharField(
                     blank=True,
                     max_length=50,
                     null=True,
                     verbose_name='Subject')),
                ('message',
                 models.TextField(
                     verbose_name='Message*')),
                ('is_resolved',
                 models.BooleanField(
                     default=False)),
                ('created',
                 models.DateTimeField(
                     auto_now_add=True)),
                ('order',
                 models.OneToOneField(
                     blank=True,
                     null=True,
                     on_delete=django.db.models.deletion.CASCADE,
                     to='orders.Order',
                     verbose_name='order')),
                ('user',
                 models.ForeignKey(
                     blank=True,
                     null=True,
                     on_delete=django.db.models.deletion.CASCADE,
                     to=settings.AUTH_USER_MODEL,
                     verbose_name='user')),
            ],
            options={
                'ordering': ['-created'],
                'verbose_name': 'Support',
                'verbose_name_plural': 'Support',
            },
        ),
    ]
