# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-02-20 01:30
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('orders', '0001_initial'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='order',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='transactions',
                to='orders.Order'),
        ),
        migrations.AddField(
            model_name='pair',
            name='base',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='base_prices',
                to='core.Currency'),
        ),
        migrations.AddField(
            model_name='pair',
            name='quote',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='quote_prices',
                to='core.Currency'),
        ),
        migrations.AddField(
            model_name='address',
            name='currency',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='core.Currency'),
        ),
        migrations.AddField(
            model_name='address',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL),
        ),
    ]