# -*- coding: utf-8 -*-


from __future__ import absolute_import

__author__ = 'frank'

import tweepy

from celery_proj.celery import app
from crawltwitter import create_app
from crawltwitter.config import load_config
from crawltwitter.models import db, AccessToken, User, Status
from crawltwitter.decorators import has_valid_application


config = load_config()


@app.task
def update_user_info():
    """更新用户信息
    取消已被取消监测但尚未被用户取消关注的用户
    抓取消息每15min执行一次，更新信息每14min执行一次
    """
    flask_app = create_app()
    with flask_app.app_context():
        # 更新用户属性
        users = User.query.all()
        accesstokens = AccessToken.query.filter_by(is_valid=True).all()
        # 利用每一个有合法access_token的用户
        for accesstoken in accesstokens:
            # 根据access_token创建针对具体应用的auth
            auth = tweepy.OAuthHandler(
                accesstoken.application.consumer_token,
                accesstoken.application.consumer_secret
            )
            auth.set_access_token(
                accesstoken.access_token, accesstoken.access_token_secret)

            api = tweepy.API(auth)
            for user in users:
                try:
                    new_user = api.get_user(user.screen_name)
                    user.name = new_user.name,
                    user.screen_name = new_user.screen_name,
                    user.location = new_user.location,
                    user.statuses_count = new_user.statuses_count,
                    user.followers_count = new_user.followers_count,
                    user.friends_count = new_user.friends_count,
                    db.session.add(user)
                except Exception, e:
                    print 'error message: %s' % e
                    print accesstoken.user.screen_name + ' access_token exceeds limit'
                    break
                print 'update_user_info success, user_id:' + user.user_id
        # 取消已被取消监测但尚未被用户取消关注的用户
        users = User.query.filter(
            User.monitor_user_id != None).filter_by(is_target=0).all()
        for user in users:
            monitor_user = User.query.filter_by(
                id=user.monitor_user_id).first()
            # 获取跟monitor_user相关的access_token，根据这个access_token来取消关注
            accesstoken = AccessToken.query.join(User).filter(
                AccessToken.is_valid == True).filter(User.id == monitor_user.id).first()
            auth = tweepy.OAuthHandler(
                accesstoken.application.consumer_token,
                accesstoken.application.consumer_secret
            )
            auth.set_access_token(
                accesstoken.access_token, accesstoken.access_token_secret)
            api = tweepy.API(auth)
            try:
                api.destroy_friendship(user.user_id)
            except Exception, e:
                print 'error message: %s' % e
                print 'call api.destroy_friendship error'
            print 'user_id:' + monitor_user.screen_name + ' call api.destroy_friendship with ' + user.screen_name + ' success'


@app.task
def crawl_home_timeline():
    """从home_timeline定期抓取消息"""
    flask_app = create_app()
    with flask_app.app_context():
        # 记录待添监测用户的user_id和id
        target_users_dict = {}
        target_users = User.query.filter_by(is_target=True).all()
        for target_user in target_users:
            target_users_dict[target_user.user_id] = target_user.id

        # 抓取每一个有合法access_token用户的homeline
        accesstokens = AccessToken.query.filter_by(is_valid=True).all()
        for accesstoken in accesstokens:
            # 根据access_token创建针对具体应用的auth
            auth = tweepy.OAuthHandler(
                accesstoken.application.consumer_token,
                accesstoken.application.consumer_secret
            )
            auth.set_access_token(
                accesstoken.access_token, accesstoken.access_token_secret)

            api = tweepy.API(auth)

            try:
                if accesstoken.user.since_id == '0':
                    # statuses为list，按照时间由新到旧排列，格式如下：
                    # [
                    #  {"created_at":"Tue Jul 29 12:06:40 +0000 2014",...},
                    #  {"created_at":"Sat Jul 26 15:41:13 +0000 2014",...},
                    #  ...,
                    # ]
                    # 第一次抓取since_id为"0"，此时写入最新的20条消息，并存入最新消息的id_str为since_id
                    statuses = api.home_timeline(page=1)
                else:
                    # ---------------------------------
                    # 考虑可能超出3000条的情况
                    # 此处直接规定count=200,　page=15, 一次性用完15min内的限额
                    # ---------------------------------
                    # 'ItemIterator' object does not support indexing
                    items = tweepy.Cursor(
                        api.home_timeline,
                        since_id=long(accesstoken.user.since_id),
                        # count=200, page=15
                    ).items(3000)
                    statuses = []
                    # statuses同样是按照时间由新到旧排列
                    for item in items:
                        statuses.append(item)
            except Exception, e:
                print 'error message: %s' % e
                print 'api.home_timeline access_token exceeds limit, retry 15min later'
                return
            # print str(len(statuses)))
            # print accesstoken.user.since_id)
            if statuses:
                # 按照时间从旧往新递增添加状态
                statuses.reverse()
                me = api.me()
                # 更新用户的属性值
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
                    # str(datetime.strptime('2015-01-22 05:51:44', "%Y-%m-%d %H:%M:%S")+timedelta(hours=8))
                    # 只添加目标用户的tweet
                    #         "created_at": "Thu Jan 22 17:20:23 +0000 2015"
                    if status.user.id_str in target_users_dict:
                        # 此处需要更新待监测目标的属性值，但考虑到api受限，并且必要性不大暂不进行
                        # -------------------------------------------------------------
                        ss = Status(status_id=status.id_str,
                                    text=status.text,
                                    created_at=status.created_at,
                                    user_id=target_users_dict[
                                        status.user.id_str],
                                    monitor_user_id=accesstoken.user.id
                                    )
                        db.session.add(ss)
                    else:
                        # celery中记录中文日志在/var/log/celery/crawltwitter-work.log会乱码
                        # 目前未解决
                        print 'user not in target_user list, userid:' + str(status.user.id_str) + '，　status_id:' + str(status.id_str)
            db.session.commit()
