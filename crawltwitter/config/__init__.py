# -*- coding: utf-8 -*-

__author__ = 'frank'

import os


def load_config():
    """加载配置类"""
    from .default import Config
    return Config
