# -*- coding: utf-8 -*-

__author__ = 'frank'

from flask.ext.wtf import Form
from wtforms import StringField, TextField, ValidationError
from models import Application


class ApplicationForm(Form):

    """添加应用信息"""

    consumer_token = StringField('consumer_token', description='准确的consumer_token')
    consumer_secret = StringField('consumer_secret', description='准确的consumer_secret')

    def validate_consumer_token(self, field):
        if Application.query.filter_by(consumer_token=field.data).first():
            raise ValidationError('该token已经被添加过，请更换合法consumer_token')

    def validate_consumer_secret(self, field):
        if Application.query.filter_by(consumer_secret=field.data).first():
            raise ValidationError('该secret已经被添加过，请更换合法consumer_secret')


class UserForm(Form):

    """添加待同步用户"""

    screen_name1 = TextField('ID1', description='准确的twitter screen_name')
    screen_name2 = TextField('ID2', description='准确的twitter screen_name')
    screen_name3 = TextField('ID3', description='准确的twitter screen_name')
    screen_name4 = TextField('ID4', description='准确的twitter screen_name')
    screen_name5 = TextField('ID5', description='准确的twitter screen_name')
