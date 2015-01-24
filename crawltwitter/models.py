# -*- coding: utf-8 -*-

__author__ = 'frank'

from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.dialects import mysql


from datetime import datetime

db = SQLAlchemy()

# 时间都存为utcnow，具体显示根据不同的本地环境进行相应转换
# 如分析数据，或者在本地显示（采用moment插件前端显示）


class Application(db.Model):

    """twitter application"""
    __tablename__ = 'applications'

    id = db.Column(db.Integer, primary_key=True)
    consumer_token = db.Column(db.String(30))
    consumer_secret = db.Column(db.String(60))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_valid = db.Column(db.Boolean, default=True)

    access_tokens = db.relationship('AccessToken', backref='application',
                                    lazy='dynamic',
                                    order_by='desc(AccessToken.created_at)')


class User(db.Model):

    """用户信息表"""
    __tablename__ = 'users'

    # 其中id用于外键链接，user_id与api交互
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
    # 下次待抓取消息id下限
    since_id = db.Column(db.String(30), default='0')
    # 是否为待监控用户
    is_target = db.Column(db.Boolean, default=False)
    # 关注者id，表明该待同步用户被monitor_user_id关注
    monitor_user_id = db.Column(mysql.INTEGER(30))
    # 图像地址
    profile_image_url = db.Column(db.String(150))
    # url 主页地址
    url = db.Column(db.String(150))

    access_tokens = db.relationship(
        'AccessToken', backref='user', lazy='dynamic', order_by='desc(AccessToken.created_at)')
    statuses = db.relationship(
        'Status', backref='user', lazy='dynamic', order_by='desc(Status.created_at)')

    def __repr__(self):
        return 'User %s' % self.screen_name


class AccessToken(db.Model):

    """access_token信息表"""
    __tablename__ = 'accesstokens'

    id = db.Column(db.Integer, primary_key=True)
    access_token = db.Column(db.String(50))
    access_token_secret = db.Column(db.String(45))
    is_valid = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(mysql.INTEGER(30), db.ForeignKey('users.id'))
    applcation_id = db.Column(db.Integer, db.ForeignKey('applications.id'))

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
    # 图片地址
    media_url = db.Column(db.String(150))


    # 被关注者id，表明该tweet是user_id发出的
    user_id = db.Column(mysql.INTEGER(30), db.ForeignKey('users.id'))
    # 关注者id，表明该tweet是id关注待同步用户之后产生的
    monitor_user_id = db.Column(mysql.INTEGER(30))

    def __repr__(self):
        print "Status %s" % self.status_id
