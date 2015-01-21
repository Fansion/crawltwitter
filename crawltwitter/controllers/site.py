# -*- coding: utf-8 -*-

__author__ = 'frank'

from flask import Blueprint, render_template, redirect, session, request, url_for, flash, current_app

import tweepy

from ..models import db, AccessToken, User, Status
from ..forms import UserForm

bp = Blueprint('site', __name__)


def clear_session():
    session.pop('access_token', None)
    session.pop('access_token_secret', None)


@bp.route('/twitter_pre_signin')
def twitter_pre_signin():
    auth = tweepy.OAuthHandler(
        current_app.config['CONSUMER_TOKEN'],
        current_app.config['CONSUMER_SECRET'],
        "http://localhost:5000/twitter_signin"
    )
    try:
        redirect_url = auth.get_authorization_url()
    except tweepy.TweepError:
        flash('Error! Failed to get request token.')
        clear_session()
        return redirect(url_for('site.index'))
    session['request_token'] = auth.request_token
    return redirect(redirect_url)


def save_user_and_token_access():
    if 'access_token' in session and 'access_token_secret' in session:
        auth = tweepy.OAuthHandler(
            current_app.config['CONSUMER_TOKEN'],
            current_app.config['CONSUMER_SECRET']
        )
        auth.set_access_token(session.get('access_token'),
                              session.get('access_token_secret'))
        api = tweepy.API(auth)
        me = api.me()
        if me:
            # 判断是否已经保存当前进行授权操作的用户
            user = User.query.filter_by(user_id=me.id_str).first()
            if user:
                accestoken = AccessToken.query.filter_by(
                    user_id=me.id_str).filter_by(is_valid=True).first()
                # 如果是否已存在合法access_token（用户可能在主页撤销授权后又重新授权）
                if accestoken:
                    if accestoken.access_token != session.get('access_token'):
                        # 保证某指定id用户只有一个合法的access_token
                        accestoken.is_valid = False
                        db.session.add(accestoken)
                        db.session.commit()
                        flash('数据表中您的旧access_token已失效')
                    else:
                        flash('数据表中已存在您的合法access_token')
                        return
            else:
                user = User(user_id=me.id_str, name=me.name, screen_name=me.screen_name, location=me.location, statuses_count=me.statuses_count,
                            followers_count=me.followers_count, friends_count=me.friends_count, created_at=me.created_at)
                db.session.add(user)
                db.session.commit()
                flash('数据表成功保存您的twitter账户信息')
            new_accesstoken = AccessToken(user_id=user.id, access_token=session.get(
                'access_token'), access_token_secret=session.get('access_token_secret'))
            db.session.add(new_accesstoken)
            db.session.commit()
            flash('数据表成功保存您的新access_token')

        else:
            flash('调用api.me失败，数据表保存access_token信息失败')
    else:
        flash('session中无可用access_token，请重新登陆')


def update_status():
    if 'access_token' in session and 'access_token_secret' in session:
        auth = tweepy.OAuthHandler(
            current_app.config['CONSUMER_TOKEN'],
            current_app.config['CONSUMER_SECRET']
        )
        auth.set_access_token(session.get('access_token'),
                              session.get('access_token_secret'))
        api = tweepy.API(auth)
        status = api.update_status('test!')
        if status:
            flash('更新状态成功')
        else:
            flash('调用api.update_status，更新状态失败')
    else:
        flash('session中无可用access_token，请重新登陆')


@bp.route('/twitter_signin')
def twitter_signin():
    auth = tweepy.OAuthHandler(
        current_app.config['CONSUMER_TOKEN'],
        current_app.config['CONSUMER_SECRET']
    )
    # request_token用完即删掉
    request_token = session.pop('request_token', None)
    auth.request_token = request_token
    verifier = request.args.get('oauth_verifier')
    try:
        auth.get_access_token(verifier)
    except tweepy.TweepError:
        flash('Error! Failed to get access token.')
        clear_session()
        return redirect(url_for('site.index'))
    # print auth.access_token, auth.access_token_secret

    session['access_token'] = auth.access_token
    session['access_token_secret'] = auth.access_token_secret

    save_user_and_token_access()
    # update_status()

    flash('登陆并授权成功')
    return redirect(url_for('site.valid_users'))


@bp.route('/crawl_user_timeline')
def crawl_user_timeline():
    from celery_proj.tasks import crawl_user_timeline
    crawl_user_timeline.delay()
    flash('正在更新数据请稍等，若数据无变化请刷新本页')
    import time
    time.sleep(3)
    return redirect(url_for('site.tweets'))


@bp.route('/valid_users')
def valid_users():
    page = request.args.get('page', 1, int)
    valid_users = User.query.join(AccessToken).filter_by(is_valid=True)
    valid_users = valid_users.paginate(page,
                                       current_app.config['USER_PER_PAGE'],
                                       error_out=True
                                       )
    return render_template('site/valid_users.html', valid_users=valid_users)


@bp.route('/target_users')
def target_users():
    page = request.args.get('page', 1, int)
    target_users = User.query.filter_by(is_target=True)
    target_users = target_users.paginate(page,
                                         current_app.config['USER_PER_PAGE'],
                                         error_out=True
                                         )
    return render_template('site/target_users.html', target_users=target_users)


@bp.route('/tweets')
def tweets():
    page = request.args.get('page', 1, int)
    statuses = Status.query.order_by(Status.created_at.desc())
    statuses = statuses.paginate(page,
                                 current_app.config['STATUS_PER_PAGE'],
                                 error_out=True
                                 )
    return render_template('site/statuses.html', statuses=statuses)


@bp.route('/add_user', methods=['GET', 'POST'])
def add_user():
    form = UserForm()
    if form.validate_on_submit():
        names = [form.screen_name1.data.strip(),
                 form.screen_name2.data.strip(),
                 form.screen_name3.data.strip(),
                 form.screen_name4.data.strip(),
                 form.screen_name5.data.strip()
                 ]
        hasName = False
        hasRepetition = False
        repeatedNames = ' '
        # 随便找一个有合法access_token账户添加目标用户，暂不考虑添加上限
        accesstoken = AccessToken.query.filter_by(is_valid=True).first()
        if not accesstoken:
            flash('数据表中无可用access_token，请用任意账户登陆授权')
            return redirect(url_for('site.twitter_pre_signin'))
        for name in names:
            if name:
                # 判断是否存在
                if not User.query.filter_by(screen_name=name).first():
                    auth = tweepy.OAuthHandler(
                        current_app.config['CONSUMER_TOKEN'],
                        current_app.config['CONSUMER_SECRET']
                    )
                    auth.set_access_token(accesstoken.access_token,
                                          accesstoken.access_token_secret
                                          )
                    api = tweepy.API(auth)
                    target_user = api.get_user(name)
                    user = User(user_id=target_user.id_str,
                                name=target_user.name,
                                screen_name=target_user.screen_name,
                                location=target_user.location,
                                statuses_count=target_user.statuses_count,
                                followers_count=target_user.followers_count,
                                friends_count=target_user.friends_count,
                                created_at=target_user.created_at, is_target=True
                                )
                    # print accesstoken.user.friends_count
                    # 如果当前有access_token尚未关注该目标用户
                    # 此时需考虑其他有合法access_token账户可能已经关注该用户，会造成status重复
                    if not target_user.id in api.friends_ids(accesstoken.user.user_id):
                        api.create_friendship(target_user.id)
                        # me = api.me()
                        # print me.friends_count
                        db.session.add(user)
                    else:
                        flash(
                            name + '已经被screen_name为' +
                            accesstoken.user.screen_name + '的人关注'
                        )
                else:
                    if name not in repeatedNames:
                        repeatedNames += ' [' + name + '] '
                    hasRepetition = True
                hasName = True
        db.session.commit()
        if hasRepetition:
            # 清空表单
            form.screen_name1.data = form.screen_name2.data = form.screen_name3.data = form.screen_name4.data = form.screen_name5.data = ''
            flash(repeatedNames + '曾被添加过,再添加些新用户吧')
            return render_template('site/add_user.html', form=form)
        if not hasName:
            flash(repeatedNames + '至少推荐一些再提交吧')
            return render_template('site/add_user.html', form=form)
        return redirect(url_for('site.target_users'))
    return render_template('site/add_user.html', form=form)


@bp.route('/')
def index():
    return render_template('site/index.html')
