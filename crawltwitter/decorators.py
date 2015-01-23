# -*- coding: utf-8 -*-

__author__ = 'frank'

from functools import wraps
from flask import abort, flash, url_for, redirect, session

from models import Application


def has_access_token(func):
    """判断session是否有合法access_token
    有则继续操作，无则提示
    """
    @wraps(func)
    def decorator(*args, **kargs):
        if 'access_token' not in session or 'access_token_secret' not in session:
            flash('session中无可用access_token，请重新登陆授权')
            return redirect(url_for('site.index'))
        return func(*args, **kargs)
    return decorator


def has_valid_application(func):
    """判断是否有合法应用，判断存在
    有则继续授权，无则跳转回主页
    """
    @wraps(func)
    def decorator(*args, **kargs):
        application = Application.query.filter_by(is_valid=True).first()
        if not application:
            flash('当前系统无合法应用，请先添加应用')
            return redirect(url_for('site.index'))
        return func(*args, **kargs)
    return decorator


def already_has_valid_application(func):
    """判断是否有合法应用，判断唯一
    有则跳转回主页，无则继续添加新应用
    """
    @wraps(func)
    def decorator(*args, **kargs):
        application = Application.query.filter_by(is_valid=True).first()
        if application:
            flash('当前系统已有合法应用，不需要继续添加')
            return redirect(url_for('site.index'))
        return func(*args, **kargs)
    return decorator
