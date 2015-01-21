# -*- coding: utf-8 -*-

__author__ = 'frank'

from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.dialects import mysql


from datetime import datetime

db = SQLAlchemy()


class User(db.Model):

    """用户信息表"""
    __tablename__ = 'users'

    # 针对于mysql数据库
    id = db.Column(mysql.INTEGER(30), primary_key=True)
    # id_str
    user_id = db.Column(db.String(30))
    name = db.Column(db.String(50))
    screen_name = db.Column(db.String(50))
    location = db.Column(db.String(30))
    statuses_count = db.Column(db.Integer)
    followers_count = db.Column(db.Integer)
    # 关注人员数, following
    friends_count = db.Column(db.Integer)
    created_at = db.Column(db.DateTime)
    # 待抓取消息id下限
    since_id = db.Column(db.String(30), default='0')
    # 是否为待监控用户
    is_target = db.Column(db.Boolean, default=False)

    access_tokens = db.relationship(
        'AccessToken', backref='user', lazy='dynamic', order_by='desc(AccessToken.created_at)')
    statuses = db.relationship(
        'Status', backref='user', lazy='dynamic', order_by='desc(Status.created_at)')

    def __repr__(self):
        print 'User %s' % self.screen_name


class AccessToken(db.Model):

    """access_token信息表"""
    __tablename__ = 'accesstokens'

    id = db.Column(db.Integer, primary_key=True)
    access_token = db.Column(db.String(50))
    access_token_secret = db.Column(db.String(45))
    is_valid = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    user_id = db.Column(mysql.INTEGER(30), db.ForeignKey('users.id'))

    def __repr__(self):
        return "AccessToken userid %d" % self.user_id


class Status(db.Model):

    """状态信息表"""
    __tablename__ = 'statuses'
    # 针对于mysql数据库
    id = db.Column(mysql.INTEGER(30), primary_key=True)
    # twitter_status_id
    status_id = db.Column(db.String(30))
    text = db.Column(db.String(150))
    created_at = db.Column(db.DateTime)

    user_id = db.Column(mysql.INTEGER(30), db.ForeignKey('users.id'))

    def __repr__(self):
        print "Status %s" % self.status_id
