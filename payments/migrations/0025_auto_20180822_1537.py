# Generated by Django 2.0.7 on 2018-08-22 15:37

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0024_merge_20180531_0724'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='currency',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, to='core.Currency'),
        ),
        migrations.AlterField(
            model_name='payment',
            name='order',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='orders.Order'),
        ),
        migrations.AlterField(
            model_name='payment',
            name='payment_preference',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, to='payments.PaymentPreference'),
        ),
        migrations.AlterField(
            model_name='payment',
            name='user',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='paymentcredentials',
            name='payment_preference',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='payments.PaymentPreference'),
        ),
        migrations.AlterField(
            model_name='paymentmethod',
            name='minimal_fee_currency',
            field=models.ForeignKey(default=4, on_delete=django.db.models.deletion.DO_NOTHING, to='core.Currency'),
        ),
        migrations.AlterField(
            model_name='paymentpreference',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='core.Location'),
        ),
        migrations.AlterField(
            model_name='paymentpreference',
            name='payment_method',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, to='payments.PaymentMethod'),
        ),
        migrations.AlterField(
            model_name='paymentpreference',
            name='push_request',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='payments.PushRequest'),
        ),
        migrations.AlterField(
            model_name='paymentpreference',
            name='tier',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='verification.VerificationTier'),
        ),
    ]
