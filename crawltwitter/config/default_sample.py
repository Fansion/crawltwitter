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
