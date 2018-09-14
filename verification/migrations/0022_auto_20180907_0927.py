# Generated by Django 2.0.7 on 2018-09-07 09:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0026_auto_20180906_1023'),
        ('verification', '0021_auto_20180903_1541'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoryRule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('modified_on', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(blank=True, max_length=255, null=True)),
                ('rule_type', models.IntegerField(choices=[(0, 'EQUAL'), (1, 'IN')])),
                ('key', models.CharField(help_text='Key of Verification payment preference payload', max_length=127)),
                ('value', models.CharField(help_text='Value of Verification payment preference payload', max_length=127)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='VerificationCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('modified_on', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(blank=True, max_length=255, null=True)),
                ('flagable', models.BooleanField(default=False)),
                ('banks', models.ManyToManyField(blank=True, help_text='This group will be add to Verification object if any of the banks from this list belogns to the payment_preferencce of that verification.', to='payments.Bank')),
                ('rules', models.ManyToManyField(blank=True, to='verification.CategoryRule')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='verification',
            name='category',
            field=models.ManyToManyField(blank=True, to='verification.VerificationCategory'),
        ),
    ]