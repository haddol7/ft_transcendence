# Generated by Django 5.1.5 on 2025-01-19 12:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('jwtapp', '0005_alter_user_table_alter_userinfo_table_and_more'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='user',
            table='user',
        ),
        migrations.AlterModelTable(
            name='userinfo',
            table='userinfo',
        ),
        migrations.AlterModelTable(
            name='userstatus',
            table='user_status',
        ),
    ]
