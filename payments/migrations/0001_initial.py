# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-12-15 22:14
from __future__ import unicode_literals

import django.db.models.deletion
import django.db.models.manager
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted', models.BooleanField(default=False)),
                ('disabled', models.BooleanField(default=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('modified_on', models.DateTimeField(auto_now=True)),
                ('nonce', models.CharField(blank=True, max_length=256, null=True, verbose_name='Nonce')),
                ('amount_cash', models.DecimalField(decimal_places=2, max_digits=12)),
                ('is_redeemed', models.BooleanField(default=False)),
                ('is_complete', models.BooleanField(default=False)),
                ('is_success', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
            managers=[
                ('active_objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='PaymentCredentials',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted', models.BooleanField(default=False)),
                ('disabled', models.BooleanField(default=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('modified_on', models.DateTimeField(auto_now=True)),
                ('uni', models.CharField(blank=True, max_length=60, null=True, verbose_name='Uni')),
                ('nonce', models.CharField(blank=True, max_length=256, null=True, verbose_name='Nonce')),
                ('token', models.CharField(blank=True, max_length=256, null=True, verbose_name='Token')),
                ('is_default', models.BooleanField(default=False, verbose_name='Default')),
                ('is_delete', models.BooleanField(default=False, verbose_name='Delete')),
            ],
            options={
                'abstract': False,
            },
            managers=[
                ('active_objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='PaymentMethod',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted', models.BooleanField(default=False)),
                ('disabled', models.BooleanField(default=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('modified_on', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('handler', models.CharField(max_length=100, null=True)),
                ('bin', models.IntegerField(default=None, null=True)),
                ('fee', models.FloatField(null=True)),
                ('is_slow', models.BooleanField(default=False)),
                ('is_internal', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PaymentPreference',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted', models.BooleanField(default=False)),
                ('disabled', models.BooleanField(default=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('modified_on', models.DateTimeField(auto_now=True)),
                ('enabled', models.BooleanField(default=True)),
                ('identifier', models.CharField(max_length=100)),
                ('comment', models.CharField(blank=True, default=None, max_length=255, null=True)),
                ('sub_type', models.CharField(blank=True, default=None, max_length=100, null=True)),
                ('main_type', models.CharField(blank=True, default=None, max_length=100, null=True)),
                ('currency', models.ManyToManyField(to='core.Currency')),
            ],
            options={
                'abstract': False,
            },
            managers=[
                ('active_objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AddField(
            model_name='payment',
            name='payment_preference',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='payments.PaymentPreference'),
        ),
    ]
