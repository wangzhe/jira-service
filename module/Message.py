# -*- coding: utf-8 -*-
import time
from optparse import Values
from module.jira import (
    execute_command,
)
from module import settings

__author__ = 'Jack'


def build_text_handler(content):
    event_handler = None
    if content.startswith(u"查看"):
        event_handler = GetEventHandler(content)
    elif content.startswith(u"报告"):
        event_handler = CreateEventHandler(content)
    return event_handler


class EventHandler(object):
    password = settings.get('PASSWORD')
    username = settings.get('USERNAME')
    system_type = settings.get('ISSUE_MNT')
    summary = settings.get('TEST_SUMMARY')
    description = settings.get('TEST_DESCRIPTION')
    reporter = settings.get('USERNAME')
    project = settings.get('PROJECT')
    occurred_time = 'customfield_10200:' + time.strftime("%d/%m/%y")

    def __init__(self, content):
        if u"运维" in content:
            self.system_type = settings.get('ISSUE_MNT')
        elif u"上线" in content:
            self.system_type = settings.get('ISSUE_PRD')
        elif u"事件" in content:
            self.system_type = settings.get('ISSUE_INT')
        elif u"反馈" in content:
            pass
        else:
            self.system_type = None

    def auth(self):
        contents = {'loglevel': 20, 'password': self.password, 'user': self.username,
                    'server': 'http://bug.xingshulin.com'}
        return Values(contents)


class CreateEventHandler(EventHandler):
    def process(self, param_summary=None, param_reporter=None):
        options = self.auth()
        args = ['create', '-s', param_summary, '-d', self.description, '-p', self.project, '-t',
                self.system_type, '-a', param_reporter, '-f', self.occurred_time]
        print args
        # execute_command(options, args)


class GetEventHandler(EventHandler):
    def process(self, param_summary=None, param_reporter=None):
        options = self.auth()
        jsql = "project = " + self.project
        if self.system_type:
            jsql += " AND type = " + self.system_type
        args = ['getissues', jsql, '10']
        results = execute_command(options, args)
        return results