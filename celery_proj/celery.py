# -*- coding: utf-8 -*-

from __future__ import absolute_import

__author__ = 'frank'

from celery import Celery
from celery.schedules import crontab

from datetime import timedelta

app = Celery('celery_proj',
             broker='redis://localhost:6379/1',
             backend='redis://localhost:6379/1',
             include=['celery_proj.tasks']
             )

app.conf.update(
    CELERY_TIMEZONE='Asia/Shanghai',
    CELERYBEAT_SCHEDULE={
        'crawl_home_timeline': {
            'task': 'celery_proj.tasks.crawl_home_timeline',
            'schedule': timedelta(minutes=15)
        }
    }
)
