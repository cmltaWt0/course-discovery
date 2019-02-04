# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-12-12 20:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course_metadata', '0138_profileimagedownloadconfig'),
    ]

    operations = [
        migrations.AddField(
            model_name='drupalpublishuuidconfig',
            name='push_people',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='drupalpublishuuidconfig',
            name='course_run_ids',
            field=models.TextField(blank=True, default=None, verbose_name='Course Run IDs'),
        ),
    ]