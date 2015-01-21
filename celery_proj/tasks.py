# -*- coding: utf-8 -*-


from __future__ import absolute_import

__author__ = 'frank'

import tweepy

from celery_proj.celery import app
from crawltwitter import create_app
from crawltwitter.config import load_config
from crawltwitter.models import db, AccessToken, User, Status


config = load_config()


@app.task
def crawl_user_timeline():
    flask_app = create_app()
    with flask_app.app_context():
        # 记录待添监测用户的user_id和id，其中id用于外键链接，user_id与api交互
        target_users_dict = {}
        target_users = User.query.filter_by(is_target=True).all()
        for target_user in target_users:
            target_users_dict[target_user.user_id] = target_user.id

        # 抓取每一个有合法access_token用户的homeline
        accesstokens = AccessToken.query.filter_by(is_valid=True).all()
        for accesstoken in accesstokens:
            auth = tweepy.OAuthHandler(
                config.CONSUMER_TOKEN, config.CONSUMER_SECRET
            )
            auth.set_access_token(
                accesstoken.access_token, accesstoken.access_token_secret)
            api = tweepy.API(auth)
            # 第一次抓取since_id为"0"，此时写入最新的20条消息，并存入最新消息的id_str为since_id
            if accesstoken.user.since_id == '0':
                # statuses为list，按照时间由新到旧排列，格式如下：
                # [
                #  {"created_at":"Tue Jul 29 12:06:40 +0000 2014",...},
                #  {"created_at":"Sat Jul 26 15:41:13 +0000 2014",...},
                #  ...,
                # ]
                # 15min　15次　考虑改变
                # statuses = api.home_timeline(page=1)
                statuses = api.user_timeline(
                    id=accesstoken.user.user_id, page=1)
            else:
                statuses = []
                # 'ItemIterator' object does not support indexing
                #
                # 15min　15次　考虑改变
                # items = tweepy.Cursor(
                # api.home_timeline,
                # since_id=long(accesstoken.user.since_id)).items()
                items = tweepy.Cursor(
                    api.user_timeline, id=accesstoken.user.user_id,
                    since_id=long(accesstoken.user.since_id)).items()
                # statuses同样是按照时间由新到旧排列
                for item in items:
                    statuses.append(item)
            print str(len(statuses))
            print accesstoken.user.since_id
            if statuses:
                # 按照时间从旧往新递增添加状态
                statuses.reverse()
                me = api.me()
                user = User.query.filter_by(user_id=me.id_str).first()
                user.name = me.name
                user.screen_name = me.screen_name
                user.since_id = statuses[-1].id_str
                user.location = me.location
                user.statuses_count = me.statuses_count
                user.followers_count = me.followers_count
                user.friends_count = me.friends_count
                db.session.add(user)
                for i, status in enumerate(statuses):
                    # status.created_at是utc时间
                    # 转为utc+8
                    # str(datetime.strptime(status.created_at, "%Y-%m-%d %H:%M:%S")+timedelta(hours=8))
                    # 只添加目标用户的tweet
                    if status.user.id_str in target_users_dict:
                        ss = Status(status_id=status.id_str,
                                    text=status.text,
                                    created_at=status.created_at,
                                    user_id=target_users_dict[
                                        status.user.id_str]
                                    )
                        db.session.add(ss)
                    else:
                        # celery中记录中文日志在/var/log/celery/crawltwitter-work.log会乱码
                        # 目前未解决
                        print 'userid:' + str(status.user.id_str) + '，　status_id:' + str(status.id_str)
            db.session.commit()
