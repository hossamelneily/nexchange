# Generated by Django 2.0.7 on 2018-09-26 14:34

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('referrals', '0009_auto_20180822_1537'),
    ]

    operations = [
        migrations.AlterField(
            model_name='referral',
            name='referee',
            field=models.OneToOneField(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='referral', to=settings.AUTH_USER_MODEL),
        ),
    ]
