# -*- coding: utf-8 -*-

__author__ = 'frank'

from flask import Flask, request, url_for, render_template, g, session, flash
from flask_debugtoolbar import DebugToolbarExtension
from flask_wtf.csrf import CsrfProtect
from flask.ext.moment import Moment

from crawltwitter.config import load_config

config = load_config()

# convert python's encoding to utf8
# 若不转换为utf-8 flash中文输出到jinjia2 html页面报错
import sys
reload(sys)
sys.setdefaultencoding('utf8')


def register_db(app):
    from models import db
    db.init_app(app)


def register_routes(app):
    from controllers import site
    app.register_blueprint(site.bp, url_prefix='')


def register_error_handle(app):
    @app.errorhandler(404)
    def page_404(error):
        return render_template('site/404.html'), 404

    @app.errorhandler(500)
    def page_500(error):
        return render_template('site/500.html'), 500


def register_moment(app):
    moment = Moment(app)


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    # CSRF protect
    CsrfProtect(app)

    if app.debug:
        DebugToolbarExtension(app)

    register_jinja(app)
    register_routes(app)
    register_db(app)
    register_error_handle(app)
    register_moment(app)

    return app


def register_jinja(app):
    # inject vars into template context
    @app.context_processor
    def inject_vars():
        return dict()

    # url generator for pagination
    def url_for_other_page(page):
        """Generate url for pagination"""
        view_args = request.view_args.copy()
        args = request.args.copy().to_dict()
        combined_args = dict(view_args.items() + args.items())
        combined_args['page'] = page
        return url_for(request.endpoint, **combined_args)

    app.jinja_env.globals['url_for_other_page'] = url_for_other_page

app = create_app()
