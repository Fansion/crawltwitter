# -*- coding: utf-8 -*-

__author__ = 'frank'

from flask.ext.script import Manager, Shell
from flask.ext.migrate import Migrate, MigrateCommand
from crawltwitter import app
from crawltwitter.models import db

manager = Manager(app)

migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)


@manager.command
def run():
    app.run(debug=True)


@manager.command
def crawl_home_timeline():

    from celery_proj.tasks import crawl_home_timeline
    crawl_home_timeline.delay()


if __name__ == '__main__':
    manager.run()
