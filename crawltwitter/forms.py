# -*- coding: utf-8 -*-

__author__ = 'frank'

from flask.ext.wtf import Form
from wtforms import StringField, TextField


class UserForm(Form):

    """添加待监测用户"""

    screen_name1 = TextField('ID1', description='准确的twitter screen_name')
    screen_name2 = TextField('ID2', description='准确的twitter screen_name')
    screen_name3 = TextField('ID3', description='准确的twitter screen_name')
    screen_name4 = TextField('ID4', description='准确的twitter screen_name')
    screen_name5 = TextField('ID5', description='准确的twitter screen_name')
