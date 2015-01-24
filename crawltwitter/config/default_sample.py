# -*- coding: utf-8 -*-

__author__ = 'frank'

import os


class Config:
    # set True in development
    DEBUG = True
    DEBUG_TB_INTERCEPT_REDIRECTS = False

    TESTING = False

    SECRET_KEY = 'SECRET_KEY'

    CONSUMER_TOKEN = 'CONSUMER_TOKEN'
    CONSUMER_SECRET = 'CONSUMER_SECRET'

    DB_HOST = 'localhost'
    DB_NAME = 'DB_NAME'
    DB_USER = 'DB_USER'
    DB_PASSWORD = 'DB_PASSWORD'
    SQLALCHEMY_DATABASE_URI = "mysql://%s:%s@%s/%s" % (
        DB_USER, DB_PASSWORD, DB_HOST, DB_NAME)
    # site.py中同时用到了session和db.session，db.session会改变实体
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    STATUS_PER_PAGE = 5
    USER_PER_PAGE = 10
    APPLICATION_PER_PAGE = 10

    CELERY_ACCEPT_CONTENT = ['pickle']

    MAX_FOLLOWERS_COUNT = 1000

    CALLBACK_URL = 'http://localhost:5000/twitter_signin'

    # 15min内api调用上限
    API_USER_SHOW_MAXIMUM = 180
    API_USER_HOME_TIMELINE_MAXIMUM = 15 * 200
