# -*- coding: utf-8 -*-

__author__ = 'frank'

import os


def load_config():
    """加载配置类"""
    mode = os.environ.get('MODE')
    if mode == 'PRODUCTION':
        from .production import ProductionConfig
        return ProductionConfig
    else:
        from .default import Config
        return Config
