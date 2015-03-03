# -*- coding: utf-8 -*-

__author__ = 'frank'

from flask import Blueprint, render_template, redirect, session, request, url_for, flash, current_app
import tweepy
from sqlalchemy import extract

from ..models import db, AccessToken, User, Status, Application
from ..forms import UserForm, ApplicationForm
from ..decorators import has_valid_application, has_access_token, already_has_valid_application
from ..filters import filter_emoji
from ..utils import get_nav_items

from datetime import datetime, timedelta
from functools import wraps
import re
import requests

bp = Blueprint('site', __name__)


def has_access_token_in_db(func):
    """判断数据库中是否有合法access_token
    有则继续操作，无则提示
    """
    @wraps(func)
    def decorator(*args, **kargs):
        accesstoken = AccessToken.query.filter_by(is_valid=True).first()
        if not accesstoken:
            flash('access_token表中无可用access_token，请重新登陆授权')
            return redirect(url_for('site.index'))
        return func(*args, **kargs)
    return decorator


def clear_session():
    session.pop('access_token', None)
    session.pop('access_token_secret', None)
    session.pop('consumer_token', None)
    session.pop('consumer_secret', None)


@has_valid_application
@has_access_token
def save_user_and_token_access():
    """在用户授权时更新用户和access_token信息"""
    application = Application.query.filter_by(is_valid=True).first()
    auth = tweepy.OAuthHandler(
        application.consumer_token,
        application.consumer_secret
    )
    auth.set_access_token(session.get('access_token'),
                          session.get('access_token_secret'))
    api = tweepy.API(auth)
    try:
        me = api.me()
    except Exception, e:
        flash('出错信息： %s' % e)
        flash('调用api.me次数超出规定上限，请15min后重试')
        return redirect(url_for('site.index'))
    if me:
        # 判断是否已经保存当前进行授权操作的用户
        user = User.query.filter_by(user_id=me.id_str).first()
        if user:
            accestoken = AccessToken.query.filter_by(
                user_id=user.id).filter_by(is_valid=True).first()
            # 如果是否已存在合法access_token（用户可能在主页撤销授权后又重新授权）
            if accestoken:
                if accestoken.access_token != session.get('access_token'):
                    # 保证某指定id用户只有一个合法的access_token
                    accestoken.is_valid = False
                    db.session.add(accestoken)
                    flash('数据表中您的旧access_token已失效')
                else:
                    flash('数据表中已存在您的合法access_token')
                    return
        else:
            user = User(user_id=me.id_str, name=me.name, screen_name=me.screen_name,
                        location=me.location, statuses_count=me.statuses_count,
                        followers_count=me.followers_count, friends_count=me.friends_count,
                        created_at=me.created_at, profile_image_url=me.profile_image_url,
                        url=me.url
                        )
            db.session.add(user)
            db.session.commit()
            flash('数据表成功保存您的twitter账户信息')
        new_accesstoken = AccessToken(user_id=user.id,
                                      access_token=session.get('access_token'),
                                      access_token_secret=session.get(
                                          'access_token_secret'),
                                      applcation_id=application.id
                                      )
        db.session.add(new_accesstoken)
        db.session.commit()
        flash('数据表成功保存您的新access_token')
    else:
        flash('调用api.me，数据表保存access_token信息失败')


@bp.route('/update_status')
@has_valid_application
def update_status():
    """更新状态，暂时用于调试"""
    application = Application.query.filter_by(is_valid=True).first()
    auth = tweepy.OAuthHandler(
        application.consumer_token,
        application.consumer_secret
    )
    #　固定设为limianmian
    auth.set_access_token('2985797091-ylbKaWogQvC93G7REiFeBKWKewaXI3fq1pU3Fgt',
                          'uDTSvK46yU9eQ1N75GDytytdWV99mBwYHf4o2necK4Q0k')
    api = tweepy.API(auth)
    try:
        status = api.update_status('test!')
    except Exception, e:
        flash('出错信息： %s' % e)
        flash('调用api.home_timeline次数超出规定上限，请15min后重试')
        return redirect(url_for('site.index'))
    if status:
        flash('更新状态成功')
    else:
        flash('调用api.update_status，更新状态失败')
    return redirect(url_for('site.index'))


@bp.route('/applications/', defaults={'page': 1})
@bp.route('/applications/<int:page>')
@has_valid_application
def applications(page):
    applications = Application.query.filter_by(is_valid=True)
    applications = applications.paginate(page,
                                         current_app.config[
                                             'APPLICATION_PER_PAGE'],
                                         error_out=True
                                         )
    return render_template('site/applications.html', applications=applications)


@bp.route('/valid_users/', defaults={'page': 1})
@bp.route('/valid_users/<int:page>')
@has_access_token_in_db
@has_valid_application
def valid_users(page):
    valid_users = User.query.join(AccessToken).filter_by(
        is_valid=True).order_by(User.id.desc())
    valid_users = valid_users.paginate(page,
                                       current_app.config['USER_PER_PAGE'],
                                       error_out=True
                                       )
    return render_template('site/valid_users.html', valid_users=valid_users)


@bp.route('/target_users/', defaults={'page': 1})
@bp.route('/target_users/<int:page>')
@has_access_token_in_db
@has_valid_application
def target_users(page):
    target_users = User.query.filter_by(
        is_target=True).order_by(User.id.desc())
    target_users = target_users.paginate(page,
                                         current_app.config['USER_PER_PAGE'],
                                         error_out=True
                                         )
    return render_template('site/target_users.html', target_users=target_users)


@bp.route('/tweets/', defaults={'page': 1})
@bp.route('/tweets/<int:page>')
def tweets(page):
    # 只显示待同步用户的推文
    statuses = Status.query.join(User).filter(
        User.is_target == True).order_by(Status.created_at.desc())
    statuses = statuses.paginate(page,
                                 current_app.config['STATUS_PER_PAGE'],
                                 error_out=True
                                 )
    target_users_count = User.query.filter_by(is_target=True).count()
    statuses_count = Status.query.count()
    return render_template('site/statuses.html', statuses=statuses, target_users_count=target_users_count, statuses_count=statuses_count)


@bp.route('/target_user/<screen_name>', defaults={'year': None, 'month': None})
@bp.route('/target_user/<screen_name>/<year>/<month>')
def target_user(screen_name, year, month):
    """优化url格式
    增加按年月查找
    """
    user = User.query.filter_by(screen_name=screen_name).first()
    earliest_tweet = Status.query.filter_by(
        user_id=user.id).order_by(Status.created_at).first()
    if earliest_tweet:
        # get list like  [('2015', '01', 'January 2015')]
        items = get_nav_items(
            str(earliest_tweet.created_at), str(datetime.utcnow()))
        nav_items = []
        for y, m, item in items:
            # search year in datetime column
            count = Status.query.filter_by(user_id=user.id).filter(extract(
                'year', Status.created_at) == y).filter(extract('month', Status.created_at) == m).count()
            # 只显示发推月份的nav_item
            if count:
                nav_items.append((y, m, item, count))
        if year and month:
            tweets = Status.query.filter_by(user_id=user.id).filter(extract('year', Status.created_at) == year).filter(
                extract('month', Status.created_at) == month).order_by(Status.created_at.desc()).all()
        else:
            tweets = Status.query.filter_by(user_id=user.id).order_by(
                Status.created_at.desc()).all()
    else:
        tweets = None
        nav_items = None

    return render_template('site/user.html', user=user, tweets=tweets, nav_items=nav_items)


@bp.route('/user/<int:id>')
def user(id):
    user = User.query.filter_by(id=id).first()
    if user:
        return redirect(url_for('site.target_user', screen_name=user.screen_name))
    else:
        return render_template('site/404.html')


@bp.route('/add_application', methods=['GET', 'POST'])
@already_has_valid_application
def add_application():
    form = ApplicationForm()
    applications = None

    if form.validate_on_submit():
        consumer_token = form.consumer_token.data.strip()
        consumer_secret = form.consumer_secret.data.strip()
        application = Application(
            consumer_token=consumer_token,
            consumer_secret=consumer_secret
        )
        db.session.add(application)
        db.session.commit()
        flash('添加应用成功')
        return redirect(url_for('site.applications'))
    return render_template('site/add_application.html', form=form)


@bp.route('/add_users', methods=['GET', 'POST'])
@has_access_token_in_db
@has_valid_application
def add_users():
    """添加待同步用户"""
    application = Application.query.filter_by(is_valid=True).first()
    auth = tweepy.OAuthHandler(
        application.consumer_token,
        application.consumer_secret
    )
    # screen_name唯一
    form = UserForm()
    if form.validate_on_submit():
        # 一个有合法access_token账户添加目标用户
        accesstokens = AccessToken.query.filter_by(is_valid=True).all()
        if not accesstokens:
            flash('数据表中无可用access_token，请用任意账户登陆授权')
            return redirect(url_for('site.twitter_pre_signin'))
        # 且考虑用户添加待同步目标上限为1000
        accesstoken = None
        for an in accesstokens:
            if an.user.followers_count < current_app.config['MAX_FOLLOWERS_COUNT']:
                accesstoken = an
                break
        if not accesstoken:
            flash('所有用户各自添加待同步用户数超过上限，请用任意新账户登陆授权')
            return redirect(url_for('site.twitter_pre_signin'))

        auth.set_access_token(
            accesstoken.access_token, accesstoken.access_token_secret)
        api = tweepy.API(auth)

        names = [form.screen_name1.data.strip(),
                 form.screen_name2.data.strip(),
                 form.screen_name3.data.strip(),
                 form.screen_name4.data.strip(),
                 form.screen_name5.data.strip()
                 ]
        hasName = False
        for name in names:
            if name:
                user = User.query.filter_by(screen_name=name).first()
                if not user:
                    try:
                        target_user = api.get_user(name)
                    except Exception, e:
                        flash('出错信息： %s' % e)
                        flash('调用api.get_user，没有找到screen_name为' + name + '的人')
                        return redirect(url_for('site.index'))
                    else:
                        user = User(user_id=target_user.id_str,
                                    name=target_user.name,
                                    screen_name=target_user.screen_name,
                                    location=target_user.location,
                                    statuses_count=target_user.statuses_count,
                                    followers_count=target_user.followers_count,
                                    friends_count=target_user.friends_count,
                                    created_at=target_user.created_at,
                                    monitor_user_id=accesstoken.user.id,
                                    is_target=True, url=target_user.url,
                                    profile_image_url=target_user.profile_image_url,
                                    )
                        # 有合法access_token的用户尚未关注该目标用户则直接关注
                        # 不需考虑其他有合法access_token账户可能已经关注该用户，造成status重复
                        # 因为is_target字段就是判断是否是目标用户进行去重的
                        if not target_user.id in api.friends_ids(accesstoken.user.user_id):
                            api.create_friendship(target_user.id)
                        else:
                            flash(
                                name + '已经被screen_name为' +
                                accesstoken.user.screen_name + '的人关注'
                            )
                        # 两种情况都需要添加该目标用户
                        # 将该用户添加为待同步用户，从home_timeline中只取目标用户的tweet
                        flash(accesstoken.user.screen_name + '成功添加新的待同步用户')
                        db.session.add(user)
                else:  # 已经在user表中
                    if user.monitor_user_id:
                        # 删除时将该字段设为false，此时需检查该字段
                        if user.is_target:
                            monitor_user = User.query.filter_by(
                                id=user.monitor_user_id).first()
                            flash(
                                name + '已经被screen_name为' + monitor_user.screen_name + '的人关注')
                        else:
                            # 重新添加已删除用户为待同步用户
                            # 改变is_target，并且需关注
                            user.is_target = True
                            db.session.add(user)
                            flash(name + '已经在user表中，原来被删除现在重新激活该用户')
                            api.create_friendship(user.user_id)
                            flash(
                                accesstoken.user.screen_name + '重新关注' + user.screen_name)
                    else:
                        flash(screen_name + '已经在user表中，再添加些新用户吧')
                hasName = True
        db.session.commit()
        if not hasName:
            flash('至少添加一些再提交吧')
            return render_template('site/add_users.html', form=form)
        return redirect(url_for('site.target_users'))
    return render_template('site/add_users.html', form=form)


@bp.route('/delete_target_user/', defaults={'user_id': None})
@bp.route('/delete_target_user/<user_id>', methods=['POST'])
def delete_target_user(user_id):
    """删除待同步用户
    策略是将该用户is_target设为False，已经抓取的推文不做处理
    但考虑到api.home_timeline抓取上限，同时需要解除关注关系
    """
    user = User.query.filter_by(
        is_target=True).filter_by(user_id=user_id).first()
    if user:
        user.is_target = False
        db.session.add(user)
        db.session.commit()
        # 此处只改变is_target，取消关注在定时任务里做
        flash('screen_name为' + user.screen_name +
              '的用户被成功删除，取消关注但仍保留已抓取的与其相关的推文')
    else:
        flash('删除用户失败')
    return redirect(url_for('site.target_users'))


@bp.route('/delete_valid_user/', defaults={'user_id': None})
@bp.route('/delete_valid_user/<user_id>', methods=['POST'])
def delete_valid_user(user_id):
    """删除已授权用户
    accestoken设置is_valid=False
    不需要直接删除user，因为显示valid_users会联合查询
    """
    accesstoken = AccessToken.query.join(User).filter(
        AccessToken.is_valid == True).filter(User.user_id == user_id).first()
    if accesstoken:
        accesstoken.is_valid = False
        db.session.add(accesstoken)
        db.session.commit()
        flash('取消授权成功')
    else:
        flash('取消授权失败')
    return redirect(url_for('site.valid_users'))


@bp.route('/delete_app/', defaults={'app_id': None})
@bp.route('/delete_app', methods=['POST'])
def delete_app(app_id):
    """删除应用"""
    application = Application.query.filter_by(id=app_id).first()
    if application:
        db.session.delete(application)
        db.session.commit()
        flash('删除应用成功')
    else:
        flash('删除应用失败')
    return redirect(url_for('site.index'))


@bp.route('/delete_status')
@has_valid_application
def delete_status():
    """删除已发状态"""
    application = Application.query.filter_by(is_valid=True).first()
    auth = tweepy.OAuthHandler(
        application.consumer_token,
        application.consumer_secret
    )
    #　固定设为limianmian
    auth.set_access_token('2985797091-ylbKaWogQvC93G7REiFeBKWKewaXI3fq1pU3Fgt',
                          'uDTSvK46yU9eQ1N75GDytytdWV99mBwYHf4o2necK4Q0k')
    api = tweepy.API(auth)

    status_ids = []
    # 上限３０００条以内
    # need to specify include_rts=True as a parameter to api.user_timeline;
    # retweets are not included by default.
    try:
        items = tweepy.Cursor(api.home_timeline, include_rts=True
                              ).items(current_app.config['API_USER_HOME_TIMELINE_MAXIMUM'])
    except Exception, e:
        flash('出错信息： %s' % e)
        flash('调用api.home_timeline次数超出规定上限，请15min后重试')
        return redirect(url_for('site.index'))

    for item in items:
        status_ids.append(item.id)

    for status_id in status_ids:
        status = api.destroy_status(status_id)
        if status:
            flash('删除状态成功')
        else:
            flash('调用api.delete_status，更新状态失败')

    return redirect(url_for('site.index'))


@bp.route('/facebook_pre_signin')
def facebook_pre_signin():
    return render_template('site/facebook_login.html')


@bp.route('/twitter_pre_signin')
@has_valid_application
def twitter_pre_signin():
    """预登陆，跳转到授权页面"""
    # 暂时只考虑有一个合法的应用
    # 理论上应该支持多个合法应用，暂时不考虑
    application = Application.query.filter_by(is_valid=True).first()
    session['consumer_token'] = application.consumer_token
    session['consumer_secret'] = application.consumer_secret
    auth = tweepy.OAuthHandler(
        session.get('consumer_token'),
        session.get('consumer_secret'),
        current_app.config['CALLBACK_URL']
    )
    try:
        redirect_url = auth.get_authorization_url()
    except tweepy.TweepError:
        flash('Error! Failed to get request token, 请重新授权')
        clear_session()
        return redirect(url_for('site.index'))
    session['request_token'] = auth.request_token
    return redirect(redirect_url)


@bp.route('/twitter_signin')
def twitter_signin():
    """登陆"""
    if session.get('consumer_token') and session.get('consumer_secret'):
        auth = tweepy.OAuthHandler(
            session.get('consumer_token'),
            session.get('consumer_secret')
        )
        # request_token用完即删掉
        request_token = session.pop('request_token', None)
        auth.request_token = request_token
        verifier = request.args.get('oauth_verifier')
        try:
            auth.get_access_token(verifier)
        except tweepy.TweepError:
            flash('Error! Failed to get access token, 请重新授权')
            clear_session()
            return redirect(url_for('site.index'))
        session['access_token'] = auth.access_token
        session['access_token_secret'] = auth.access_token_secret

        save_user_and_token_access()
        # update_status()

        flash('登陆并授权成功')
        return redirect(url_for('site.valid_users'))
    else:
        flash('session中无可用consumer_token和consumer_secret，请先授权新用户')
        return redirect(url_for('site.index'))


@bp.route('/crawl_home_timeline')
@has_valid_application
def crawl_home_timeline():
    """从home_timeline定期抓取消息
    用于页面辅助手动更新，用于调试　
    """
    # from celery_proj.tasks import crawl_home_timeline
    # crawl_home_timeline.delay()

    # 记录待添同步用户的user_id和id
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

        statuses = []
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
                ).items(current_app.config['API_USER_HOME_TIMELINE_MAXIMUM'])
                # statuses同样是按照时间由新到旧排列
                for item in items:
                    statuses.append(item)
        except Exception, e:
            flash('出错信息： %s' % e)
            flash('调用api.home_timeline次数超出规定上限，请15min后重试')
            return redirect(url_for('site.index'))
        # flash(str(len(statuses)))
        # flash(accesstoken.user.since_id)
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
                    # 此处需要更新待同步目标的属性值，但考虑到api受限，并且必要性不大暂不进行
                    # -------------------------------------------------------------
                    # 将推文插入数据库时会出现4个字节的emoji符号编码，无法插入utf8的mysql数据库
                    if hasattr(status, 'extended_entities'):
                        ss = Status(status_id=status.id_str,
                                    text=filter_emoji(status.text),
                                    created_at=status.created_at,
                                    user_id=target_users_dict[
                                        status.user.id_str],
                                    monitor_user_id=accesstoken.user.id,
                                    media_url=status.extended_entities['media'][
                                        0]['media_url']
                                    )
                    else:
                        ss = Status(status_id=status.id_str,
                                    text=filter_emoji(status.text),
                                    created_at=status.created_at,
                                    user_id=target_users_dict[
                                        status.user.id_str],
                                    monitor_user_id=accesstoken.user.id,
                                    )
                    db.session.add(ss)
                else:
                    # celery中记录中文日志在/var/log/celery/crawltwitter-work.log会乱码
                    # 目前未解决
                    print 'user not in target_user list, userid:' + str(status.user.id_str) + '，　status_id:' + str(status.id_str)
            db.session.commit()
    flash('正在更新数据请稍等，若数据无变化请刷新本页')
    import time
    time.sleep(2)
    return redirect(url_for('site.tweets'))


@bp.route('/update_user_info')
def update_user_info():
    # 更新用户属性信息
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
                user.name = new_user.name
                user.screen_name = new_user.screen_name
                user.location = new_user.location
                user.statuses_count = new_user.statuses_count
                user.followers_count = new_user.followers_count
                user.friends_count = new_user.friends_count
                user.profile_image_url = new_user.profile_image_url
                db.session.add(user)
            except Exception, e:
                print 'error message: %s' % e
                print accesstoken.user.screen_name + ' access_token exceeds limit'
                break
            print 'update_user_info success, user_id:' + user.user_id
        db.session.commit()
    # 取消已被取消同步但尚未被用户取消关注的用户
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
        print 'user_id:' + monitor_user.user_id + ' call api.destroy_friendship with ' + user.user_id + ' success'
    return render_template('site/index.html')

# 表单数据只能从request.args接收
# @bp.route('/search/<keyword>/<int:page>')
# @bp.route('/search/<keyword>/', defaults={'page': 1})
# @bp.route('/search/', defaults={'keyword': None, 'page': 1})


@bp.route('/search/', defaults={'page': 1})
@bp.route('/search/<int:page>')
def search(page):
    """模糊查找指定内容的推文"""
    keyword = request.args.get("keyword", '')
    if not keyword:
        flash('请输入要查找的推文关键字')
        return redirect(url_for('site.tweets'))
    else:
        statuses = Status.query.filter(
            Status.text.like('%' + keyword + '%')).order_by(Status.created_at.desc())
        statuses_count = len(statuses.all())
        statuses = statuses.paginate(page,
                                     current_app.config['STATUS_PER_PAGE'],
                                     error_out=True
                                     )
        if not statuses.items:
            flash('抱歉，未找到与"' + keyword + '"相关的推文')
            return redirect(url_for('site.tweets'))
        else:
            return render_template('site/statuses.html', statuses=statuses, statuses_count=statuses_count)


@bp.route('/strict_search/', defaults={'page': 1})
@bp.route('/strict_search/<int:page>')
def strict_search(page):
    keyword = request.args.get("keyword", '')
    if not keyword:
        flash('请输入要查找的推文关键字')
        return render_template('site/strict_search_results.html')
    else:
        # 从接口中读模糊查询结果并显示
        url = current_app.config['QUERY_URL']
        rets = requests.get(url % keyword).json()
        if rets:
            docs = rets['response']['docs']
            # 使用paginate组件对docs　list进行分页,并传递到common.html中进行页面显示
            from paginate import Page
            my_page = Page(
                docs, page=page, items_per_page=current_app.config['ITEMS_PER_PAGE'])
            return render_template('site/strict_search_results_with_new_paginator.html', my_page=my_page)
        else:
            flash('抱歉，未找到与"' + keyword + '"相关的推文')
            return render_template('site/strict_search_results.html')

        # 直接从数据表中模糊查询
        # statuses = Status.query.filter(
        #     Status.text.like('%' + keyword + '%')).order_by(Status.created_at.desc())
        # statuses_count = len(statuses.all())
        # statuses = statuses.paginate(page,
        #                              current_app.config['STATUS_PER_PAGE'],
        #                              error_out=True
        #                              )
        # if not statuses.items:
        #     flash('抱歉，未找到与"' + keyword + '"相关的推文')
        #     return render_template('site/strict_search_results.html')
        # else:
        # return render_template('site/strict_search_results.html',
        # statuses=statuses, statuses_count=statuses_count)


@bp.route('/')
def about():
    return render_template('site/about.html')
    # return redirect(url_for('site.strict_search'))


@bp.route('/dev')
def dev():
    return render_template('site/dev.html')


@bp.route('/index')
def index():
    return render_template('site/index.html')
