# -*- coding: utf-8 -*-
import time
from optparse import Values
from module.jira import (
    execute_command,
)
from module import settings

__author__ = 'Jack'


password = settings.get('PASSWORD')
username = settings.get('USERNAME')
system_type = settings.get('ISSUE_MNT')
summary = settings.get('TEST_SUMMARY')
description = settings.get('TEST_DESCRIPTION')
reporter = settings.get('USERNAME')
project = settings.get('PROJECT')
occurred_time = 'customfield_10200:' + time.strftime("%d/%m/%y")


def build_text_handler(content):
    event_handler = None
    if u"运维" in content:
        event_handler = CreateEventHandler(settings.get('ISSUE_MNT'))
    elif u"查看" in content:
        event_handler = GetEventHandler()
    elif u"上线" in content:
        event_handler = CreateEventHandler(settings.get('ISSUE_PRD'))
    elif u"事件" in content:
        event_handler = CreateEventHandler(settings.get('ISSUE_INT'))
    elif u"反馈" in content:
        pass
    else:
        pass
    return event_handler


class EventHandler:

    def __init__(self, sys_type):
        self.system_type = sys_type

    def auth(self):
        contents = {'loglevel': 20, 'password': password, 'user': username, 'server': 'http://bug.xingshulin.com'}
        return Values(contents)


class CreateEventHandler(EventHandler):

    def process(self, param_summary=summary, param_reporter=reporter):
        options = self.auth()
        args = ['create', '-s', param_summary, '-d', self.description, '-p', self.project, '-t',
                self.system_type, '-a', param_reporter, '-f', self.occurred_time]
        print args
        # execute_command(options, args)


class GetEventHandler(EventHandler):

    def __init__(self):
        pass

    def process(self, param_summary=summary, param_reporter=reporter):
        options = self.auth()
        args = ['getissues', 'project = JCTP']
        results = execute_command(options, args)
        return results