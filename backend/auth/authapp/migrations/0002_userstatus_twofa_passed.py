# Generated by Django 5.1.5 on 2025-01-21 08:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userstatus',
            name='twofa_passed',
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
    ]
