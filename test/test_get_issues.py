import time
from optparse import Values
from module.jira import (
    execute_command,
)
from test import settings


password = settings.get('PASSWORD')
username = settings.get('USERNAME')
summary = settings.get('TEST_SUMMARY')
description = settings.get('TEST_DESCRIPTION')
reporter = settings.get('USERNAME')
project = settings.get('PROJECT')
system_type = settings.get('ISSUE_MNT')
occurred_time = 'customfield_10200:' + time.strftime("%d/%m/%y")

if (__name__ == "__main__"):
    contents = {'loglevel': 20, 'password': password, 'user': username, 'server': 'http://bug.xingshulin.com'}
    options = Values(contents)
    jsql = 'project = JCTP and type = ' + settings.get('ISSUE_PRD')
    args = ['getissues', jsql, '5']
    results = execute_command(options, args)
    print results
