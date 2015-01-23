# -*- coding: utf-8 -*-

__author__ = 'frank'

from .default import Config


class ProductionConfig(Config):

    SECRET_KEY = 'W{8cCC(0,4<D9nth0*2Btat~6OW198'

    CALLBACK_URL = 'http://crawller.ifanan.com/twitter_signin'
