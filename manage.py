# -*- coding: utf-8 -*-

__author__ = 'frank'

from flask.ext.script import Manager, Shell
from flask.ext.migrate import Migrate, MigrateCommand
from crawltwitter import app
from crawltwitter.models import db, Application, User, AccessToken, Status

manager = Manager(app)

migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)


def make_context():
    return dict(app=app, db=db, Application=Application, User=User, AccessToken=AccessToken, Status=Status)
manager.add_command('shell', Shell(make_context=make_context))


@manager.command
def run():
    app.run(debug=True)


@manager.command
def crawl_home_timeline():

    from celery_proj.tasks import crawl_home_timeline
    crawl_home_timeline.delay()


if __name__ == '__main__':
    manager.run()
