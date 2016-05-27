# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-05-26 20:38
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0017_auto_20160525_0001'),
    ]

    operations = [
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('modified_on', models.DateTimeField(auto_now=True)),
                ('deleted', models.BooleanField(default=False)),
                ('disabled', models.BooleanField(default=False)),
                ('type', models.CharField(choices=[('W', 'WITHDRAW'), ('D', 'DEPOSIT')], max_length=1)),
                ('address', models.CharField(max_length=32)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            managers=[
                ('active_objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('modified_on', models.DateTimeField(auto_now=True)),
                ('type', models.CharField(choices=[('W', 'WITHDRAW'), ('D', 'DEPOSIT')], max_length=1)),
                ('is_verified', models.BooleanField()),
                ('address_from', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='address_from', to='core.Address')),
                ('address_to', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='address_to', to='core.Address')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Order')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='payment',
            name='user',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transaction',
            name='payment',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Payment'),
        ),
    ]