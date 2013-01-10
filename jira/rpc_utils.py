#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys

from suds.client import Client

from jira import settings


class JiraException(Exception):
    pass


class RPCException(Exception):
    def __init__(self, env, *args, **kwargs):
        self.message = 'env: %s' % str(env)
        super(self, RPCException).__init__(*args, **kwargs)


def setup_logging(loglevel=logging.INFO):
    """Set up logging, by default just echo to stdout."""
    logger = logging.getLogger()
    logger.setLevel(loglevel)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(loglevel)

    formatter = logging.Formatter("%(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


def get_project_choices(env):
    """Concatentate the names of values in a structure."""
    results = ""
    first_choice = True
    for i, v in enumerate(env['projects']):
        if first_choice:
            results = "%s (%s)" % (v['name'], v['key'])
            first_choice = False
        else:
            results += ", %s (%s)" % (v['name'], v['key'])
    return results


def get_field_id(name, fields):
    result = 'unknown'

    matches = [x['id'] for x in fields if x['name'] == name]
    if len(matches):
        result = matches[0]

    return result


def change_status(issue_id, action, env, logger, **kwargs):
    """Generic function for changing the status of an issue."""
    client = env['client']
    auth = env['auth']

    try:
        actions = client.service.getAvailableActions(auth, issue_id)
    except Exception, e:
        logger.error(e)

    action_id = ''
    for i, v in enumerate(actions):
        if v['name'] == action:
            action_id = v['id']
            break

    if action_id == '':
        logger.error('Unable to perform action: ' + action)
        logger.error('Choices are: ')
        for i, v in enumerate(actions):
            logger.info(v['name'] + ' (' + v['id'] + ')')
        return 1

    if 'resolution' in kwargs:
        resolution = kwargs['resolution']
    else:
        resolution = '1'

    if 'timetracking' in kwargs:
        timetracking = kwargs['timetracking']
    else:
        timetracking = '0m'

    try:
        return client.service.progressWorkflowAction(
            auth, issue_id, action_id,
            [
                {"id": "assignee", "values": [env['jirauser']]},
                {"id": "resolution", "values": [resolution]},
                {"id": "timetracking", "values": [timetracking]},
            ]
        )
    except Exception, e:
        logger.error(e)


def get_client(logger):
    WSDL_URL = settings.get('WSDL_URL')

    try:
        logger.debug('Attempting to connect to the server: ' + WSDL_URL)

        client = Client(WSDL_URL)
        logger.debug('Connected to the server')
        logger.debug(client)
        return client
    except Exception, e:
        logger.error('Failed to connect to JIRA (%s): %s' % (WSDL_URL, e))
        raise


def rpc_init(logger):
    env = dict(
        jirauser=settings.get('USERNAME'),
    )

    authorized = False
    while not authorized:
        try:
            logger.debug('Starting authorization')

            client = get_client(logger)
            auth = client.service.login(
                env['jirauser'], settings.get('PASSWORD'),
            )

            logger.debug('Using auth to get types')
            env['types'] = client.service.getIssueTypes(auth)

            logger.debug('Using auth to get subtask types')
            env['subtypes'] = client.service.getSubTaskIssueTypes(auth)

            logger.debug('Using auth to get statuses')
            env['statuses'] = client.service.getStatuses(auth)

            logger.debug('Using auth to get priorities')
            env['priorities'] = client.service.getPriorities(auth)

            logger.debug('Using auth to get resolutions')
            env['resolutions'] = client.service.getResolutions(auth)

            logger.debug('Using auth to get projects')
            env['projects'] = client.service.getProjectsNoSchemes(auth)

            authorized = True

            env['client'] = client
            env['auth'] = auth
        except Exception, e:
            logger.error('Error authenticating with JIRA')
            logger.exception(e)
            raise

    return env
