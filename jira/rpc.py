#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Core RPC code.
#
# Heavily modified version of the python CLI
# https://plugins.atlassian.com/plugin/details/10751

import types

from datetime import datetime
from suds.sax.date import DateTime as sudsdatetime

from jira import settings
from jira.rpc_utils import (
    change_status, rpc_init, setup_logging, get_project_choices, get_field_id,
    JiraException, RPCException,
)

log = setup_logging()


class Project(object):
    """Class representing a project in JIRA.

    This holds all methods for accessing, updating, and creating content in
    JIRA via SOAP. Project-level seemed like a good entry point since that's
    the base unit of aggregation in JIRA. There is no explicit class
    representing an issue (or anything else); anything requiring access to an
    issue, eg: `add_comment` just takes an issue ID as a parameter.

    Usage:

    >>> from jira.rpc import Project
    >>> p = Project('TEST')
    >>> result = p.create_issue('Test issue using all available defaults')
    >>> p.add_comment(result['key'], 'First comment on the new issue!')

    """
    def __init__(self, project_id):
        self.env = rpc_init(log)

        if settings.get('TESTING'):
            log.debug('Overriding JIRA project from %s to TEST' % project_id)
            project_id = settings.get('TEST_PROJECT')

        projects = get_project_choices(self.env)
        if project_id not in projects:
            raise JiraException("%s isn't a valid project ID." % project_id)

        self.project_id = project_id

        client = self.env['client']
        auth = self.env['auth']
        server_info = client.service.getServerInfo(auth)
        log.debug("Server info: %s" % server_info)

        if 'auth' not in self.env or not self.env['auth']:
            log.critical("Error acquiring auth token")
            raise RPCException(self.env)

        if 'client' not in self.env or not self.env['client']:
            log.critical("Error acquiring client")
            raise RPCException(self.env)

    def create_issue(self, summary, assignee=None, priority='Major',
                     issue_type='Task', description=None, estimate=None,
                     parent_id=None, affects_versions=None, fix_versions=None):
        """Create an issue in JIRA. Only requires a summary.

        To create sub-tasks, simply pass in the parent ID as ``parent_id``.

        """
        client = self.env['client']
        auth = self.env['auth']

        try:
            self.env['fieldnames'] = client.service.getCustomFields(auth)
        except Exception:
            # In case we don't have permission to get the fields
            self.env['fieldnames'] = [{'id':-1, 'name':'unavailable'}]

        priority_id = 0
        for i, v in enumerate(self.env['priorities']):
            if v['name'] == priority:
                priority_id = v['id']

        if priority_id == 0:
            raise JiraException('Unknown priority: ' + priority)

        issue_type_id = 0
        if parent_id:
            for i, v in enumerate(self.env['subtypes']):
                if v['name'] == issue_type:
                    issue_type_id = v['id']
        else:
            for i, v in enumerate(self.env['types']):
                if v['name'] == issue_type:
                    issue_type_id = v['id']

        if issue_type == 0:
            log.error('Unknown issue type: %s' % issue_type)
            log.error(
                'Known issue types: %s' %
                ", ".join(map(lambda i: i['name'], self.env['types']))
            )
            log.error(
                'Known subtask issue types: %s' %
                ", ".join(map(lambda i: i['name'], self.env['subtypes']))
            )

            raise JiraException("Unknown issue type %s" % issue_type)

        remote_issue = {
            "project": self.project_id,
            "type": issue_type_id,
            "summary": summary,
            "priority": priority_id,
            "description": description,
            "assignee": assignee,
        }

        if affects_versions:
            remote_issue['affectsVersions'] = affects_versions

        if fix_versions:
            remote_issue['fixVersions'] = fix_versions

        if not parent_id:
            return client.service.createIssue(auth, remote_issue)
        else:
            return client.service.createIssueWithParent(
                auth, remote_issue, parent_id,
            )

    def add_comment(self, issue_id, comment):
        if not issue_id or not comment:
            raise JiraException("Issue ID and comment text are both required.")

        client = self.env['client']
        auth = self.env['auth']
        try:
            return client.service.addComment(
                auth, issue_id, dict(body=comment))
        except Exception, e:
            log.error(e)
            raise

    def close_issue(self, issue_id):
        action = 'Close Issue'
        return change_status(issue_id, action, self.env, log)

    def reopen_issue(self, issue_id):
        action = 'Reopen Issue'
        return change_status(issue_id, action, self.env, log)

    def resolve_issue(self, issue_id):
        action = 'Resolve Issue'
        return change_status(self.issue_id, action, self.env, log)

    def update_issue_attribute(self, issue_id, field, value):
        if type(value) in types.StringTypes:
            value = value.split(',')
        client = self.env['client']
        auth = self.env['auth']

        fields = [
            'key', 'summary', 'reporter', 'assignee', 'description',
            'environment', 'project', 'type', 'status', 'priority',
            'resolution', 'duedate', 'originalEstimate', 'timeLogged',
            'votes',
        ]
        if field not in fields and not field.startswith("customfield_"):
            try:
                self.env['fieldnames'] = client.service.getCustomFields(auth)
            except:
                # In case we don't have permission to get the fields
                self.env['fieldnames'] = [{'id': -1, 'name': 'unavailable'}]

            cn = get_field_id(field, self.env['fieldnames'])
            if cn == "unknown":
                raise JiraException(
                    "Field name '%s' not found in %s" %
                         (field, fields + self.env['fieldnames'])
                )
            self.field = cn
        return client.service.updateIssue(
            auth, issue_id, [{'id': field, 'values': value}]
        )

    def add_version(self, version_name, release_date):
        release_date = datetime.strptime(release_date, '%Y-%m-%d')
        client = self.env['client']
        auth = self.env['auth']

        try:
            # https://fedorahosted.org/suds/ticket/219
            # seems to be fixed in 0.3.9
            dateObj = sudsdatetime(release_date)
            version = client.factory.create('ns0:RemoteVersion')
            version.name = version_name
            version.releaseDate = dateObj
            version.archived = False
            version.released = False

            return client.service.addVersion(auth, self.project_id, version)
        except Exception, e:
            log.error(e)
            raise JiraException(e)
