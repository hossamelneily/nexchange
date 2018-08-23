# Generated by Django 2.0.7 on 2018-08-22 15:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('referrals', '0008_auto_20180223_1407'),
    ]

    operations = [
        migrations.AlterField(
            model_name='referral',
            name='code',
            field=models.ForeignKey(default=None, help_text='Use this link to refer users and earn free Bitcoins', null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='referrals.ReferralCode'),
        ),
    ]
