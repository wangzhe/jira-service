#!/usr/bin/python
#
# JIRA CLI
#
# (c) Consulting Toolsmiths. 2007-2010
# (c) XenSource, Inc. 2006
#

from optparse import OptionParser
import base64
import getopt
import getpass
import logging
import os
import string
import sys
from suds.sax.text import Text
import time
from datetime import datetime
import urllib

# Add the suds library to the front of sys.path and make it work from
# locations other than the script's home directory
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), 'python-suds-0.3.9'))
from suds.client import Client
from suds.sax.date import DateTime as sudsdatetime

# Note: if you change the SOAP RPC plugin, then change the endpoint too because
# suds caches the methods it sees as available.

# The proxy object for the JIRA server
soap = None
# The authentication token
auth = None


class JiraCommand:
    name = "<default>"
    aliases = []
    summary = "<--- no summary --->"
    usage = ""
    mandatory = ""

    commands = None

    def __init__(self, commands):
        self.commands = commands

    def dispatch(self, logger, jira_env, args):
        """Return the exit code of the whole process"""
        if len(args) > 0 and args[0] in ("--help", "-h"):
            logger.info("")
            alias_text = ''
            first_alias = True
            for a in self.aliases:
                if first_alias:
                    if len(self.aliases) == 1:
                        alias_text = " (alias: " + a
                    else:
                        alias_text = " (aliases: " + a
                    first_alias = False
                else:
                    alias_text += ", " + a
            if not first_alias:
                alias_text += ")"
            logger.info("%s: %s%s" % (self.name, self.summary, alias_text))
            if self.usage == "":
                opts = ""
            else:
                opts = " [options]"
            logger.info("")
            logger.info("Usage: %s %s %s%s" % \
                        (sys.argv[0], self.name, self.mandatory, opts))
            logger.info(self.usage)
            return 0
        results = self.run(logger, jira_env, args)
        if results:
            return self.render(logger, jira_env, args, results)
        else:
            return 1

    def run(self, logger, jira_env, args):
        """Return a non-zero object for success"""
        return 0

    def render(self, logger, jira_env, args, results):
        """Return 0 for success"""
        return 0


class JiraHelp(JiraCommand):
    name = "help"
    summary = "Get a summary of commands, -v shows all details"

    def run(self, logger, jira_env, args):
        progname = sys.argv[0]
        show_api = False
        if len(args) > 0 and (args[0] == '-v'):
            show_api = True
        logger.info("")
        logger.info("%s [options] <command>" % (progname))
        logger.info("")
        logger.info("where <command> is one of:")
        logger.info("")
        shown = {}
        for c in self.commands.getall():
            if shown.has_key(c.name):
                continue
            else:
                shown[c.name] = 1
            logger.info("%-10s %s" % (c.name, c.summary))
            if show_api:
                logger.info("%s" % (c.usage))

        logger.info("")
        logger.info("\"%s <command> --help\" provides more usage information"
                    % (progname))
        logger.info("")
        return 1


class JiraAttach(JiraCommand):
    name = "attach"
    summary = "Attach a file to an issue"
    usage = """
    <issue key>           Issue identifier, e.g. CA-1234
    <filename>            The file to be attached
    <name>                A name for the attachment in JIRA
    """

    def run(self, logger, jira_env, args):
        global soap, auth
        if len(args) != 3:
            logger.error(self.usage)
        issueKey = args[0]
        filename = args[1]
        name = args[2]

        fp = open(filename, 'rb')
        file_contents = fp.read()
        fp.close()
        file_contents = file_contents.encode('base64')
        name = name.encode("utf-8")
        try:
            return soap.service.addBase64EncodedAttachmentsToIssue(auth,
                                                                   issueKey,
                                                                   [name],
                                                                   [file_contents])
            return 0
        except Exception, e:
            logger.error(e)


class JiraCat(JiraCommand):
    name = "cat"
    summary = "Show all the fields in an issue"
    usage = """
    <issue key>           Issue identifier, e.g. CA-1234
    """

    def run(self, logger, jira_env, args):
        global soap, auth
        if len(args) != 1:
            logger.error(self.usage)
            return 0
        issueKey = args[0]
        try:
            jira_env['fieldnames'] = soap.service.getFieldsForEdit(auth, issueKey)
        except Exception, e:
            # In case we don't have edit permission
            jira_env['fieldnames'] = {}
        try:
            return soap.service.getIssue(auth, issueKey)
        except Exception, e:
            logger.error(decode(e))

    def render(self, logger, jira_env, args, results):
        # For available field names, see the variables in
        # src/java/com/atlassian/jira/rpc/soap/beans/RemoteIssue.java
        fields = jira_env['fieldnames']
        for f in ['key', 'summary', 'reporter', 'assignee', 'description',
                  'environment', 'project',
                  'votes'
        ]:
            logger.info(getName(f, fields) + ': ' + encode(results[f]))

        logger.info('Type: ' + getName(results['type'], jira_env['types']))
        logger.info('Status: ' + getName(results['status'], jira_env['statuses']))
        logger.info('Priority: ' + getName(results['priority'], jira_env['priorities']))
        logger.info('Resolution: ' + getName(results['resolution'], jira_env['resolutions']))
        for f in ['created',
                  # 'updated',
                  'duedate'
        ]:
            logger.info(getName(f, fields) + ': ' + dateStr(results[f]))

        for f in ['updated',
        ]:
            logger.info('%s: %s' % (getName(f, fields), results[f]))

        for f in results['components']:
            logger.info(getName('components', fields) + ': ' + encode(f['name']))
        for f in results['affectsVersions']:
            logger.info(getName('versions', fields) + ': ' + encode(f['name']))
        for f in results['fixVersions']:
            logger.info('Fix Version/s:' + encode(f['name']))

        # TODO bug in JIRA api - attachmentNames are not returned
        # logger.info(str(results['attachmentNames']))

        # TODO restrict some of the fields that are shown here
        for f in results['customFieldValues']:
            fieldName = str(f['customfieldId'])
            for v in f['values']:
                logger.info(getName(fieldName, fields) + ': ' + encode(v))

        return 0


class JiraCatAndComments(JiraCommand):
    """An example of combining the output of two commands"""

    name = "catall"
    summary = "Show all the fields and comments in an issue"
    usage = """
    <issue key>           Issue identifier, e.g. CA-1234
    """

    def run(self, logger, jira_env, args):
        command = JiraCat(self.commands)
        results = command.run(logger, jira_env, args)
        if results:
            logger.info("")
            logger.info("Contents")
            logger.info("--------")
            command.render(logger, jira_env, args, results)
            logger.info("")
            logger.info("Comments")
            logger.info("--------")
        else:
            return 0
        command = JiraComments(self.commands)
        results = command.run(logger, jira_env, args)
        if results:
            command.render(logger, jira_env, args, results)
        else:
            return 0


class JiraComment(JiraCommand):
    name = "comment"
    summary = "Add a comment to an issue"
    usage = """
    <issue key>           Issue identifier, e.g. CA-1234
    <text>                Text of the comment
    """

    def run(self, logger, jira_env, args):
        global soap, auth
        issueKey = args[0]
        message = args[1]
        if len(args) != 2 or issueKey == None or message == None:
            logger.error(self.usage)
            return 0
        try:
            # TODO may have to do it this way with Python 2.6?
            # comment = client.factory.create('ns0:RemoteComment')
            # comment.body = 'This is a comment'
            return soap.service.addComment(auth, issueKey, {"body": message})
        except Exception, e:
            logger.error(decode(e))


class JiraComments(JiraCommand):
    name = "comments"
    summary = "Show all the comments about an issue"
    usage = """
    <issue key>           Issue identifier, e.g. CA-1234
    """

    def run(self, logger, jira_env, args):
        global soap, auth
        if len(args) != 1:
            logger.error(self.usage)
            return 0
        issueKey = args[0]
        logger.debug('Comments of issue ' + issueKey)
        try:
            return soap.service.getComments(auth, issueKey)
        except Exception, e:
            logger.error(decode(e))

    def render(self, logger, jira_env, args, results):
        for i, v in enumerate(results):
            logger.info('[' + dateStr(v['created']) + '] ' + encode(v['author']) + ':')
            logger.info(encode(v['body']))
            logger.info('')
        return 0


def getFieldId(name, fields):
    '''TODO cache this, and note getCustomFields() needs admin privilege'''
    if name == None:
        return "None"
    if fields == None:
        return name
    for i, v in enumerate(fields):
        val = v['id']
        if v['name'] == name:
            return v['id']
    return "unknown"


class JiraCreate(JiraCommand):
    name = "create"
    summary = "Create an issue"
    usage = """
    -p <project>
    -s <summary>
    -d <description>
    -e <estimate>
    [-a assignee]
    [-c component]
    [-r <affects version ids>]
    [-t <type>]
    [-u <fix version ids>]
    [-z priority]
    [-f fieldname:value1,value2]
    [-y parent issue key]

Type 'jira create' for more detail on these options.
    """

    def run(self, logger, jira_env, args):
        global soap, auth

        parser = OptionParser("usage: create <arguments>")
        parser.add_option("-s", "--summary", dest="summary",
                          help="Summary of the new issue")
        parser.add_option("-d", "--description", dest="description",
                          help="Description of the new issue")
        parser.add_option("-e", "--estimate", dest="estimate",
                          help="Estimate of how long the new issue will take, e.g. 1h30m")

        # Add the project keys too
        project_choices = getProjectChoicesStr(jira_env['projects'])
        parser.add_option("-p", "--project", dest="project",
                          help="Project in which to create new issue, Choices: %s " % project_choices)
        parser.add_option("-a", "--assignee", dest="assignee", default=jira_env['jirauser'],
                          help="User to whom the issue is assigned, default: %default")
        priority_choices = getChoicesStr(jira_env['priorities'])
        parser.add_option("-z", dest="priority", default="Major",
                          help="Priority of the issue, default: %default.\nChoices: " + priority_choices)
        type_choices = getChoicesStr(jira_env['types']) + ". Sub-tasks: " + getChoicesStr(jira_env['subtypes'])

        parser.add_option("-c", "--components", dest="components",
                          default=None,
                          help="The comma-separated ids of components")

        parser.add_option("-r", "--affectsversions", dest="affectsversions",
                          default=None,
                          help="The comma-separated ids of affects versions")
        parser.add_option("-u", "--fixversions", dest="fixversions",
                          default=None,
                          help="The comma-separated ids of fix versions")
        parser.add_option("-t", "--type", dest="issuetype", default="Bug",
                          help="Type of issue, default: %default.\nChoices: " + type_choices)
        parser.add_option("-y", "--parent", dest="parent", default="",
                          help="If set, then a subtask is created with the given parent issue, e.g. JRA-123")

        try:
            jira_env['fieldnames'] = soap.service.getCustomFields(auth)
        except Exception, e:
            # In case we don't have permission to get the fields
            jira_env['fieldnames'] = [{'id': -1, 'name': 'unavailable'}]
        cf_choices = getChoicesStr(jira_env['fieldnames'])
        parser.add_option("-f", "--field", dest="customfield",
                          default=[], action="append",
                          help="Custom field name and comma-separated values. E.g. -f \"field name 1:a,b\" -f \"field name 2:hello world\"\nChoices: %s" % cf_choices)
        (options, args) = parser.parse_args(args)

        # Check that the arguments with no defaults have been set
        if options.summary == None:
            parser.print_help()
            return 0

        try:
            priority = 0
            for i, v in enumerate(jira_env['priorities']):
                if v['name'] == options.priority:
                    priority = v['id']
            if priority == 0:
                logger.error('Unknown priority: ' + options.priority)
                return 0

            issuetype = 0
            for i, v in enumerate(jira_env['types']):
                if convertText2Str(v['name']) == options.issuetype:
                    issuetype = v['id']

            if issuetype == 0:
                for i, v in enumerate(jira_env['subtypes']):
                    if v['name'] == options.issuetype:
                        issuetype = v['id']
                if issuetype != 0 and options.parent == "":
                    logger.error(
                        'Issue type "' + options.issuetype + '" is a subtask so must have a parent issue specified')
                    return 0

            if issuetype == 0:
                logger.error('Unknown issue type: ' + options.issuetype)
                logger.error('Known issue types: ' + ", ".join(map(lambda i: i['name'], jira_env['types'])))
                logger.error('Known subtask issue types: ' + ", ".join(map(lambda i: i['name'], jira_env['subtypes'])))
                return 0

            cfv = []
            for cf in options.customfield:
                cn_raw, cv = cf.split(':')
                if not cn_raw.startswith("customfield_"):
                    cn = getFieldId(cn_raw, jira_env['fieldnames'])
                    if cn == "unknown":
                        logger.error("Field name '%s' not found in %s" % (cn_raw, cf_choices))
                        return 0
                else:
                    cn = cn_raw
                    # To create a cascading select, pass both the parent and
                    # child values and add +1 to the child, e.g.
                    # -f "customfield_10004:10200" -f "customfield_10004+1:10300"
                    if "+" in cn_raw:
                        pk_key, pk_val = cn_raw.split('+')
                        cn = pk_key + ':' + pk_val

                cfv.append([
                    {'customfieldId': cn, 'values': [cv.split(',')]}
                ])

            fixVersions = []
            if options.fixversions:
                for v in options.fixversions.split(','):
                    version = {'id': v.strip()}
                    fixVersions.append(version)

            affectsVersions = []
            if options.affectsversions:
                for v in options.affectsversions.split(','):
                    version = {'id': v.strip()}
                    affectsVersions.append(version)

            components = []
            if options.components:
                for c in options.components.split(','):
                    component = {'id': c.strip()}
                    components.append(component)

            remoteIssue = {
                "project": options.project,
                "type": issuetype,
                "summary": options.summary.decode('utf-8'),
                "priority": priority,
                "description": options.description.decode('utf-8'),
                "assignee": options.assignee,
                "customFieldValues": cfv,
            }
            # "components": components,
            # "affectsVersions": affectsVersions,
            # "fixVersions": fixVersions,
            if options.parent == "":
                issue = soap.service.createIssue(auth, remoteIssue)
                return issue
            else:
                methods = soap.wsdl.services[0].ports[0].methods.keys()
                if methods.has_key('createSubtask'):
                    return soap.service.createSubtask(auth, remoteIssue, options.parent)
                else:
                    logger.error('The current JIRA server does not support the command: createSubtask')
        except Exception, e:
            logger.exception(e)
            # logger.error(decode(e))

    def render(self, logger, jira_env, args, results):
        logger.info('Created issue ' + results['key'])
        return 0


def changeStatus(issueKey, action):
    """Generic function for changing the status of an issue"""
    global soap, auth
    try:
        actions = soap.service.getAvailableActions(auth, issueKey)
    except Exception, e:
        logger.error(decode(e))
    actionId = ''
    for i, v in enumerate(actions):
        if v['name'] == action:
            actionId = v['id']
            break
    if actionId == '':
        logger.error('Unable to perform action: ' + action)
        logger.error('Choices are: ')
        for i, v in enumerate(actions):
            logger.info(v['name'] + ' (' + v['id'] + ')')
        return 1
    # TODO using defaults for resolution and timetracking but should
    # accept values from args too
    resolution = '1'
    timetracking = '1m'
    try:
        return soap.service.progressWorkflowAction(auth, issueKey, actionId, [
            {"id": "assignee", "values": [jira_env['jirauser']]},
            {"id": "resolution", "values": [resolution]},
            {"id": "timetracking", "values": [timetracking]},
        ])
    except Exception, e:
        logger.error(decode(e))


class JiraClose(JiraCommand):
    name = "close"
    summary = "Move an issue to the Closed state"
    usage = """
    <issue key>           Issue identifier, e.g. CA-1234
    """

    def run(self, logger, jira_env, args):
        if len(args) != 1:
            logger.error(self.usage)
            return 0
        issueKey = args[0]
        action = 'Close Issue'
        return changeStatus(issueKey, action)


class JiraReopen(JiraCommand):
    name = "reopen"
    summary = "Move an issue to the Reopened state"
    usage = """
    <issue key>           Issue identifier, e.g. CA-1234
    """

    def run(self, logger, jira_env, args):
        if len(args) != 1:
            logger.error(self.usage)
            return 0
        issueKey = args[0]
        action = 'Reopen Issue'
        return changeStatus(issueKey, action)


class JiraResolve(JiraCommand):
    name = "resolve"
    aliases = ["fix"]
    summary = "Move an issue to the Resolved state"
    usage = """
    <issue key>           Issue identifier, e.g. CA-1234
    """

    def run(self, logger, jira_env, args):
        if len(args) != 1:
            logger.error(self.usage)
            return 0
        issueKey = args[0]
        action = 'Resolve Issue'
        return changeStatus(issueKey, action)


class JiraLink(JiraCommand):
    name = "link"
    summary = "Link one issue to another"
    usage = """
    NOT YET IMPLEMENTED
    <from issue key>         Issue identifier to link from, e.g. CA-1234
    <to issue key>           Issue identifier to link to, e.g. CA-1235
    """

    def run(self, logger, jira_env, args):
        global soap, auth
        logger.error(self.usage)
        return 0


class JiraLogin(JiraCommand):
    name = "login"
    summary = "Login to JIRA"
    usage = """
    [userid]         Use a different userid to login to JIRA
    """

    def run(self, logger, jira_env, args):
        global soap, auth
        if len(args) != 2:
            logger.error(self.usage)
            return 0
        if args[0] != None:
            jirauser = args[0]
        else:
            jirauser = raw_input('user: ')

        if args[1] != None:
            password = args[1]
        else:
            password = getpass.getpass('password: ')

        try:
            auth = soap.service.login(jirauser, password)
            # Write the authentication token (not password) to a file
            # for use next time
            jirarc_file = jira_env['home'] + os.sep + '.jirarc'
            fp = open(jira_env['jirarc_file'], 'wb')
            fp.write(jirauser + '\n')
            fp.write(auth + '\n')
            fp.close()
            return auth
        except Exception, e:
            logger.error("Login failed")
            # logger.error(e)


class JiraLogout(JiraCommand):
    name = "logout"
    summary = "Log out of JIRA before the session is timed out"
    usage = """
    """

    def run(self, logger, jira_env, args):
        global soap, auth
        if len(args) > 0:
            logger.error(self.usage)
            return 0
        try:
            auth = soap.service.logout(auth)
            # Delete the authentication token (not password) from a file
            jirarc_file = jira_env['home'] + os.sep + '.jirarc'
            if os.path.exists(jirarc_file):
                os.remove(jirarc_file)
            return 1
        except Exception, e:
            logger.exception(e)
            logger.error("Logout failed")


class JiraProjects(JiraCommand):
    name = "projects"
    summary = "Show all the projects in JIRA"
    usage = """
    """

    def run(self, logger, jira_env, args):
        if len(args) != 0:
            logger.error(self.usage)
            return 0
        return 1

    def render(self, logger, jira_env, args, results):
        for i, v in enumerate(jira_env['projects']):
            # For available field names, see the variables in
            # src/java/com/atlassian/jira/rpc/soap/beans/RemoteProject.java
            logger.info('%s (%s)' % (v['name'], v['key']))
            if v['description'] != None:
                logger.info('%s' % (v['description']))
            logger.info('')
        return 0


class JiraGetIssues(JiraCommand):
    name = "getissues"
    summary = "List issues that match a JQL query. Shows issue key, created and summary fields sorted by created. Requires JIRA 4.x"
    usage = """
   "<JQL query>"             JQL query, e.g. "Summary ~ '%some%text%' AND Reporter=nagios AND Created > -7d"
   [<limit>]                   Optional limit to number of issues returned, default 100
   """

    def run(self, logger, jira_env, args):
        global soap, auth
        if len(args) == 2:
            limit = int(args[1])
            args = args[0].decode('utf-8')
        elif len(args) == 1:
            args = args[0].decode('utf-8')
            limit = 100
        else:
            logger.error(self.usage)
            return 0
        issues = soap.service.getIssuesFromJqlSearch(auth, args, limit)
        return issues

    def render(self, logger, jira_env, args, results):
        def compareCreated(a, b):
            if a == None:
                return b
            if b == None:
                return a
            return cmp(a['created'], b['created'])

        logger.info('key,created,summary')
        cmd_results = ''
        for issue in sorted(results, compareCreated):
            occoured_time = encode(issue['customFieldValues'][0]['values'][0])
            result = ':\r\n'.join([occoured_time, unicode(issue['summary']), ])
            cmd_results = cmd_results + result + '\r\n \r\n'
            logger.info(result)
        return cmd_results


class JiraReport(JiraCommand):
    name = "report"
    summary = "Run a report already defined in JIRA"
    usage = """
    <report name>           Name or id of the report, e.g. "My report" or 10491
    """

    def run(self, logger, jira_env, args):
        global soap, auth
        if len(args) != 1:
            logger.error(self.usage)
            return 0
        reportName = args[0]
        try:
            reportNumber = string.atoi(reportName)
        except ValueError:
            # Find the report number from the report name
            reportNumber = 0
            try:
                reports = soap.service.getSavedFilters(auth)
            except Exception, e:
                logger.error(decode(e))

            for i, v in enumerate(reports):
                if v['name'] == reportName:
                    reportNumber = v['id']
                    jira_env['reportName'] = reportName
                    break
            if reportNumber == 0:
                logger.error('Unable to find report named \'' + reportName + '\'')
                return 1
        try:
            jira_env['reportNumber'] = reportNumber
            return soap.service.getIssuesFromFilter(auth, str(reportNumber))
        except Exception, e:
            logger.error(decode(e))

    def render(self, logger, jira_env, args, results):
        if jira_env.has_key('reportName'):
            reportName = jira_env['reportName']
        else:
            reportName = str(jira_env['reportNumber'])
        logger.info('Report \'' + reportName + '\', ' + str(len(results)) + ' issues')
        logger.info('%s\t%s\t%s' % ('Key', 'Assignee', 'Summary'))
        for i, v in enumerate(results):
            # For available field names, see the variables in
            # src/java/com/atlassian/jira/rpc/soap/beans/RemoteIssue.java
            logger.info('%s\t%s\t%s' % (v['key'], v['assignee'], v['summary']))
        return 0


class JiraCreateUser(JiraCommand):
    name = "createusers"
    summary = "Create new users, needs administrator permission"
    usage = """
    """

    def run(self, logger, jira_env, args):
        global soap, auth
        try:

            groupname = "jira-developers"
            group = soap.service.getGroup(auth, groupname)
            # TODO this code needs to be edited to fit the local file of users
            fd = open('/Users/mdoar/users.txt')
            for line in fd.readlines():
                if line.startswith('#') or line.strip() == "":
                    continue
                chunks = line.split(',')
                username = chunks[0]
                fullname = chunks[1]
                # Decode fullname only into unicode
                fullname = unicode(fullname, encoding="utf-8")
                email = chunks[2].strip()
                password = 'secret'
                print "Creating %s, %s, %s" % (username, fullname, email)
                soap.service.createUser(auth, username, password, fullname, email)
                user = soap.service.getUser(auth, username)
                try:
                    soap.service.addUserToGroup(auth, group, ruser=user)
                except Exception, e:
                    print "%s is already a member of %s" % (username, groupname)
            fd.close
            return 0
        except Exception, e:
            logger.exception(e)


class JiraDeactivateUser(JiraCommand):
    name = "deactivateusers"
    summary = "Deactivate users, needs administrator permission."
    usage = """
    """

    # Remove from all groups, add zzz prefix to name, change email to invalid
    def run(self, logger, jira_env, args):
        global soap, auth
        try:

            # Other odd ones:
            # anybody@zinio.com pjamieson@zinio.com	Anybody Interested
            active_userids = [
                # '', #Rangnekar Shantanu
                # '', #Spirupolo Jorge
                'admin',
                'blynn',
                'ashishp@bsquare.com',
                'bmeduri',  # Meduri Bala
                'choonyap',  # Yap Choon Hong
                'craigl@bsquare.com',
                'dbrandt',
                'eheiker',  #Heiker Eric
                'erauer',  #Rauer Eric
                'ereeves',  #Reeves Eric
                'ericj@bsquare.com',
                'gstinerman',  #Stinerman Gennady
                'jcastro',  #deCastro. Jose
                'jgarcia',  #Garcia Joe
                'jlang',  #Jeff Lang
                'kkuram',  #Kuram Kalyan
                'llau',  #Leidyne Lau
                'lrepas',
                'lrepas',  #Repas Lester
                'lswanson',  #Jacobson Lana
                'mabraham',  #Mary Abraham
                'mdoar',
                'mmcginty',  #McGinty Meg
                'mniebla',  #Mario Niebla
                'ppolinsky',  #Polinsky Peter
                'preddy@zinio.com',  #Praveen Reddy
                'pvasireddy',  #Praveen Vasireddy
                'rshenoy',  #Shenoy Radha
                'schen',  #Chen Shirley
                'steve',  #Dere Steve
                'vdjamgarov@zinio.com',  #Vlad Djamgarov
                'venkatb@bsquare.com',
                'wcummings',  #Cummings Wes,
            ]

            jira_group_names = [  # 'atg-dev',
                                  # 'jira-administrators',
                                  # 'jira-atg',
                                  # 'jira-balthaser',
                                  #'jira-bi',
                                  #'jira-bus-solutions',
                                  #'jira-dbas',
                                  #'jira-developers',
                                  #'jira-ecom',
                                  #'jira-facilities',
                                  #'jira-gnws',
                                  #'jira-iphone',
                                  #'jira-itcorp',
                                  #'jira-itops',
                                  #'jira-pm',
                                  'jira-qa',
                                  #'jira-reader',
                                  #'jira-readermac',
                                  #'jira-readerwin',
                                  #'jira-tools',
                                  'jira-users',
            ]
            # Set up the group objects
            jira_groups = {}
            for group_name in jira_group_names:
                logger.info("Getting users in group %s" % group_name)
                group = soap.service.getGroup(auth, group_name)
                jira_groups[group_name] = group

            jirausers_group = jira_groups['jira-users']
            jirausers = jirausers_group['users']

            # Check the active users all exist
            active_users_checked = {}
            for userid in active_userids:
                active_users_checked[userid] = False
                logger.info("Checking that userid %s exists" % userid)
                for user in jirausers:
                    if user['name'] == userid:
                        # The user exists
                        active_users_checked[userid] = True
            problem = False
            for userid in active_users_checked:
                if not active_users_checked[userid]:
                    problem = True
                    logger.error("Failed to find user " + userid)
            if problem:
                return 1

            # Change the user profile details
            if True:
                for user in jirausers:
                    userid = user['name']
                    if userid not in active_userids:
                        if True:
                            fullname = user['fullname']
                            # Clean up
                            if fullname.startswith("zzz zzz "):
                                fullname = fullname.replace("zzz zzz ", "")
                            if not fullname.startswith('zzz '):
                                fullname = 'zzz ' + fullname
                            email = user['email'].replace('.com', '.invalid')
                            logger.info(
                                "Changing user profile for  %s to fullname=%s and email=%s" % (userid, fullname, email))
                            soap.service.updateUser(auth, userid, fullname, email)
                    elif False:
                        fullname = user['fullname']
                        email = user['email']
                        if fullname.startswith('zzz '):
                            fullname = fullname.replace('zzz ', '')
                            if fullname.startswith('zzz '):
                                fullname = fullname.replace('zzz ', '')
                            soap.service.updateUser(auth, userid, fullname, email)
                        elif email.find('invalid') != -1 and not email.endswith('zinio.com'):
                            # Some userids are actually email addresses
                            if userid.find('@') != -1:
                                email = '%s' % (userid)
                            else:
                                email = '%s@zinio.com' % (userid)

                            logger.info("Fixing active user %s email to %s" % (userid, email))
                            soap.service.updateUser(auth, userid, fullname, email)

            # Remove from all the specified groups
            if True:
                for group_name in jira_groups:
                    # The users in this group
                    users = group['users']
                    logger.info("Found %s users in group %s" % (len(users), group_name))

                    for user in users:
                        userid = user['name']
                        fullname = user['fullname']
                        # Decode fullname only into unicode
                        # fullname = unicode(fullname, encoding="utf-8")
                        email = user['email']

                        if userid not in active_userids:
                            logger.info("Removing %s from %s" % (userid, group_name))
                            soap.service.removeUserFromGroup(auth, group, user)

            return 0
        except Exception, e:
            logger.exception(e)


class JiraListUsers(JiraCommand):
    name = "listusers"
    summary = "List users, needs administrator permission"
    usage = """
    """

    def run(self, logger, jira_env, args):
        global soap, auth
        try:
            groupname = "jira-users"
            group = soap.service.getGroup(auth, groupname)
            return group['users']
        except Exception, e:
            logger.exception(e)

    def render(self, logger, jira_env, args, results):
        def compare(a, b):
            if a == None:
                return b
            if b == None:
                return a
            return cmp(a['fullname'], b['fullname'])

        for user in sorted(results, compare):
            if user['name'] not in ['authad']:
                logger.info("%s,%s,%s" % (user['name'], user['fullname'], user['email']))
        logger.info("%d users" % len(results))
        return 0


class JiraSyncVersions(JiraCommand):
    name = "syncversions"
    summary = "Synchronize versions from one project to another"
    usage = """
    <source project>              Project key, e.g. TSTONE
    <destination project>         Project key, e.g. TSTTWO
    """

    def run(self, logger, jira_env, args):
        global soap, auth
        if len(args) != 2:
            logger.error(self.usage)
            return 0
        src_project = args[0]
        dst_project = args[1]
        try:
            src_versions = soap.service.getVersions(auth, src_project)
            dst_versions = soap.service.getVersions(auth, dst_project)
            dst_vnames = [n['name'] for n in dst_versions]
            for version in src_versions:
                # Versions may not be uniquely identified by name but
                # for the purposes of synchronization they are
                if version['name'] in dst_vnames:
                    logger.info('Version %s is already in project %s' % (version['name'], dst_project))
                else:
                    logger.info("Adding version %s to project %s" % (version['name'], dst_project))
                    date = version['releaseDate']
                    if date:
                        pythonDate = datetime(int(date[0]),
                                              int(date[1]),
                                              int(date[2]),
                                              int(date[3]),
                                              int(date[4]),
                                              int(date[5]),
                                              0
                        )
                        dateObj = sudsdatetime(pythonDate)

                    else:
                        dateObj = None
                    # See comment in AddVersion about why sequence etc
                    # are not copied
                    versionObj = {'name': version['name'],
                                  'releaseDate': dateObj,
                                  # 'archived': version['archived'],
                                  # 'released': version['released'],
                    }
                    soap.service.addVersion(auth, dst_project, remoteVersion=versionObj)
            return 0
        except Exception, e:
            logger.exception(e)


class JiraSyncComponents(JiraCommand):
    name = "synccomps"
    summary = "Synchronize components from one project to another"
    usage = """
    <source project>              Project key, e.g. TSTONE
    <destination project>         Project key, e.g. TSTTWO
    """

    def run(self, logger, jira_env, args):
        global soap, auth
        if len(args) != 2:
            logger.error(self.usage)
            return 0
        src_project = args[0]
        dst_project = args[1]
        try:
            src_components = soap.service.getComponents(auth, src_project)
            dst_components = soap.service.getComponents(auth, dst_project)
            dst_names = [n['name'] for n in dst_components]
            for component in src_components:
                # Components are uniquely identified by name
                if component['name'] in dst_names:
                    logger.info('Component %s is already in project %s' % (component['name'], dst_project))
                else:
                    # JIRA doesn't have addComponent yet,so use REST
                    # e.g. http://localhost:8080/jira/secure/project/AddComponent.jspa?name=Component&description=Description&componentLead=admin&pid=10002
                    # Also RemoteComponent only has the name value but
                    # http://jira/secure/project/AddComponent.jspa?name=ComponentB&pid=10061 also works
                    pkey = None
                    for proj in jira_env['projects']:
                        if proj['key'] == dst_project:
                            pkey = proj['id']
                            break
                    if not pkey:
                        logger.error('Unable to find id for project %s' % dst_project)
                        return 1
                    # Handle component names with spaces in them
                    comp_name = urllib.quote_plus(component['name'])
                    # TODO get the user password again for REST
                    # TODO replace the URL with the local one
                    url = 'http://jira/secure/project/AddComponent.jspa?name=%s&pid=%s&os_username=%s&os_password=secret' % (
                        comp_name, pkey, jira_env['jirauser'])
                    logger.info(
                        "Adding component %s to project %s using REST: %s" % (component['name'], dst_project, url))
                    urllib.urlopen(url).close()
            return 0
        except Exception, e:
            logger.exception(e)


class JiraAddUserToGroup(JiraCommand):
    name = "addusertogroup"
    summary = "Add a user to a group, needs administrator permission"
    usage = """
    <username>             User id, e.g. jsmith
    <group>                Group name, e.g. jira-developers
    """

    def run(self, logger, jira_env, args):
        global soap, auth
        if len(args) != 2:
            logger.error(self.usage)
            return 0
        username = args[0]
        groupname = args[1]
        try:
            user = soap.service.getUser(auth, username)
            group = soap.service.getGroup(auth, groupname)
            # This action is idempotent and will not complain if a user
            # is already in a group
            return soap.service.addUserToGroup(auth, group, ruser=user)
        except Exception, e:
            logger.exception(e)
            logger.error(decode(e))


class JiraRemoveUserFromGroup(JiraCommand):
    name = "removeuserfromgroup"
    summary = "Remove a user from a group, needs administrator permission"
    usage = """
    <username>             User id, e.g. jsmith
    <group>                Group name, e.g. jira-developers
    """

    def run(self, logger, jira_env, args):
        global soap, auth
        if len(args) != 2:
            logger.error(self.usage)
            return 0
        username = args[0]
        groupname = args[1]
        try:
            user = soap.service.getUser(auth, username)
            group = soap.service.getGroup(auth, groupname)
            # This action is idempotent and will not complain if a user
            # is not in a group
            return soap.service.removeUserFromGroup(auth, group, ruser=user)
        except Exception, e:
            logger.error(decode(e))


class JiraReports(JiraCommand):
    name = "reports"
    summary = "List all the available reports"
    usage = """
    """

    def run(self, logger, jira_env, args):
        global soap, auth
        try:
            return soap.service.getSavedFilters(auth)
        except Exception, e:
            logger.error(decode(e))

    def render(self, logger, jira_env, args, results):
        logger.info('%s\t%s\t%s' % ('Id', 'Name', 'Author'))
        for i, v in enumerate(results):
            # For available field names, see the variables in
            # src/java/com/atlassian/jira/rpc/soap/beans/RemoteFilter.java
            logger.info('%s\t%s\t%s' % (v['id'], v['name'], v['author']))
        return 0


class JiraDeleteProject(JiraCommand):
    name = "deleteproject"
    summary = "Delete a JIRA project"
    usage = """
    <project>                Project key, e.g. TST
    """

    def run(self, logger, jira_env, args):
        global soap, auth
        if len(args) != 1:
            logger.error(self.usage)
            return 0
        pkey = args[0]
        try:
            soap.service.deleteProject(auth, pkey)
        except Exception, e:
            logger.exception(e)
            logger.error(decode(e))


class JiraAddVersion(JiraCommand):
    name = "addversion"
    summary = "Add a new version, needs administrator permission"
    usage = """
    <project>              Project key, e.g. TST
    <versionname>          Name of the version
    <date>                 Release date, YYYY:MM:DD
    """
    # <schedule>             The id of the version in the list of versions?

    def run(self, logger, jira_env, args):
        global soap, auth
        if len(args) != 3:
            logger.error(self.usage)
            return 0
        project = args[0]
        versionname = args[1]
        # RemoteVersion does not support the description
        year, month, day = args[2].split(':')
        # schedule = int(args[3])
        try:
            # https://fedorahosted.org/suds/ticket/219 seems to be fixed in 0.3.9
            pythonDate = datetime(int(year), int(month), int(day), 0, 0, 0, 0)
            dateObj = sudsdatetime(pythonDate)
            version = {}
            version['name'] = versionname
            version['releaseDate'] = dateObj
            version['archived'] = False
            version['released'] = True

            # Doesn't seem to have any effect. Could expose another move method?
            # version.sequence: 1000 but does this need to be suds.sax.long or such like?

            return soap.service.addVersion(auth, project, version)
        except Exception, e:
            print e
            logger.exception(e)
            # logger.error(decode(e))


class JiraUpdate(JiraCommand):
    name = "update"
    summary = "Update the contents of an issue"
    usage = """
    <issue key>           Issue identifier, e.g. CA-1234
    <field>               Name of field to update
    <value>               New value or comma-separated values for the field
    """

    def run(self, logger, jira_env, args):
        global soap, auth
        if len(args) != 3:
            logger.error(self.usage)
            return 0
        issueKey = args[0]
        fieldName = args[1]
        newValue = args[2].split(',')
        try:
            # TODO there must be a better way to get this info
            # and getFieldsForEdit isn't it? Basically all the private fields
            # of RemoteField.java
            std_fieldnames = [
                'key', 'summary', 'reporter', 'assignee', 'description',
                'environment', 'project', 'type', 'status', 'priority', 'resolution',
                'duedate', 'originalEstimate', 'timeLogged', 'votes',
            ]
            if fieldName not in std_fieldnames and not fieldName.startswith("customfield_"):
                try:
                    jira_env['fieldnames'] = soap.service.getCustomFields(auth)
                except Exception, e:
                    # In case we don't have permission to get the fields
                    jira_env['fieldnames'] = [{'id': -1, 'name': 'unavailable'}]
                cn = getFieldId(fieldName, jira_env['fieldnames'])
                if cn == "unknown":
                    logger.error(
                        "Field name '%s' not found in %s" % (fieldName, std_fieldnames + jira_env['fieldnames']))
                    return 0
                fieldName = cn
            return soap.service.updateIssue(auth, issueKey, [
                {'id': fieldName,
                 'values': newValue}
            ])
        except Exception, e:
            logger.exception(e)


class JiraUpdateCSS(JiraCommand):
    name = "updatecss"
    summary = "Update the contents of a custom cascading select field in an issue"
    usage = """
    <issue key>           Issue identifier, e.g. CA-1234
    <field>               Name of field to update, e.g. customfield_10010
    <value>               New value as comma-separated optionids, e.g. 10011,10014. Values can be found from the links on the fields' option configuration page
    """

    def run(self, logger, jira_env, args):
        global soap, auth
        if len(args) != 3:
            logger.error(self.usage)
            return 0
        issueKey = args[0]
        fieldName = args[1]
        parentValue, childValue = args[2].split(',')
        try:
            if not fieldName.startswith("customfield_"):
                try:
                    jira_env['fieldnames'] = soap.service.getCustomFields(auth)
                except Exception, e:
                    # In case we don't have permission to get the fields
                    jira_env['fieldnames'] = [{'id': -1, 'name': 'unavailable'}]
                cn = getFieldId(fieldName, jira_env['fieldnames'])
                if cn == "unknown":
                    logger.error(
                        "Field name '%s' not found in %s" % (fieldName, std_fieldnames + jira_env['fieldnames']))
                    return 0
                fieldName = cn

            fieldValues = [
                {'id': fieldName,
                 'values': [parentValue]},
                {'id': fieldName + ':1',
                 'values': [childValue]},
            ]
            logger.error("GOT %s" % fieldValues)
            return soap.service.updateIssue(auth, issueKey, fieldValues)
        except Exception, e:
            logger.exception(e)


class JiraDev(JiraCommand):
    name = "dev"
    summary = "Template for testing API commands"
    usage = """
    """

    def run(self, logger, jira_env, args):
        global soap, auth
        if len(args) != 0:
            logger.error(self.usage)
            return 0
        # issueKey = args[0]
        try:
            return soap.service.getServices(auth)
        except Exception, e:
            logger.exception(e)

    def render(self, logger, jira_env, args, results):
        for i, v in enumerate(results):
            logger.info('Name: ' + encode(v['name']))
            logger.info('Description: ' + encode(v['description']))
            logger.info('Delay: ' + encode(v['delay']) + 'ms')
            logger.info('Last run: ' + encode(v['lastRun']))
            logger.info("")
        return 0


class JiraUnitTest(JiraCommand):
    name = "foo"
    summary = "Run unit tests on the JIRA CLI"
    usage = """
    """

    def run(self, logger, jira_env, args):
        import doctest

        global soap, auth
        if len(args) != 0:
            logger.error(self.usage)
            return 0
        logger = MockLogger()
        logger.debug('Running unit tests ...')
        globs = {'com': com,
                 'logger': logger,
                 'jira_env': jira_env,
                 'args': args,
        }
        verbosity = False
        if options.loglevel < logging.INFO:
            verbosity = True
        doctest.testfile("../foo/cli/CliTests.log", verbose=verbosity, extraglobs=globs,
                         optionflags=doctest.REPORT_UDIFF)
        logger.debug('Finished unit tests')


class Commands:
    def __init__(self):
        self.commands = {}
        self.add(JiraAddUserToGroup)
        self.add(JiraAddVersion)
        self.add(JiraAttach)
        self.add(JiraCat)
        self.add(JiraCatAndComments)
        self.add(JiraClose)
        self.add(JiraComment)
        self.add(JiraComments)
        self.add(JiraCreate)
        self.add(JiraCreateUser)
        self.add(JiraDeactivateUser)
        self.add(JiraDeleteProject)
        self.add(JiraHelp)
        self.add(JiraListUsers)
        self.add(JiraLogin)
        self.add(JiraLogout)
        self.add(JiraProjects)
        self.add(JiraRemoveUserFromGroup)
        self.add(JiraReopen)
        self.add(JiraReport)
        self.add(JiraGetIssues)
        self.add(JiraReports)
        self.add(JiraResolve)
        self.add(JiraSyncComponents)
        self.add(JiraSyncVersions)
        self.add(JiraUnitTest)
        self.add(JiraUpdate)
        self.add(JiraUpdateCSS)

    def add(self, cl):
        # TODO check for duplicates in commands
        c = cl(self)
        self.commands[c.name] = c
        for a in c.aliases:
            self.commands[a] = c

    def has(self, command):
        return self.commands.has_key(command)

    def run(self, command, logger, jira_env, args):
        """Return the exit code of the whole process"""
        return self.commands[command].dispatch(logger, jira_env, args)

    def getall(self):
        keys = self.commands.keys()
        keys.sort()
        return map(self.commands.get, keys)


def encode(s):
    '''Deal with unicode in text fields'''
    if s == None:
        return "None"
    if type(s) == unicode or type(s) == Text:
        s = s.encode("utf-8")
    return str(s)


def dateStr(i):
    '''Convert a datetime or String object to a string output format'''
    if i == None or i == 'None':
        return str(i)
    # JIRA 4.4 returns a datetime object
    if hasattr(i, 'date'):
        return "%04d/%02d/%02d %02d:%02d:%02d" % (i.year, i.month, i.day, i.hour, i.minute, i.second)
    return "%04d/%02d/%02d %02d:%02d:%02d" % (i[0], i[1], i[2], i[3], i[4], i[5])


def convertText2Str(id):
    '''Convert id to str'''
    if type(id) == Text:
        id = id.encode('utf-8')
    return str(id)


def getName(id, fields):
    '''TODO cache this, and note getCustomFields() needs admin privilege'''
    if id == None:
        return "None"
    if fields == None:
        return convertText2Str(id)
    for i, v in enumerate(fields):
        val = v['id']
        if val and val.lower() == id.lower():
            return convertText2Str(v['name'])
    return convertText2Str(id.title())


def getChoicesStr(fields):
    """Concatentate the names of values in a structure"""
    results = ""
    first_choice = True
    for i, v in enumerate(fields):
        if first_choice:
            results = v['name']
            first_choice = False
        else:
            results += ", " + v['name']
    return results


def getProjectChoicesStr(fields):
    """Concatentate the names of values in a structure"""
    results = ""
    first_choice = True
    for i, v in enumerate(fields):
        if first_choice:
            results = "%s (%s)" % (v['name'], v['key'])
            first_choice = False
        else:
            results += ", %s (%s)" % (v['name'], v['key'])
    return results


def decode(e):
    """Process an exception for useful feedback"""
    # TODO how to log the fact it is an error, but allow info to be unchanged?
    # TODO now fault not faultstring?
    # The faultType class has faultcode, faultstring and detail
    str = e.faultstring
    if str == 'java.lang.NullPointerException':
        return "Invalid issue key?"
    return e.faultstring


def setupLogging(loglevel=logging.INFO):
    """Set up logging, by default just echo to stdout"""
    logger = logging.getLogger()
    logger.setLevel(loglevel)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(loglevel)
    # TODO logging.getLogger('suds.client').setLevel(logging.DEBUG), suds.transport etc
    formatter = logging.Formatter("%(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


class MockLogger:
    """Print the output to stdout for doctest to check."""

    def __init__(self): pass

    def info(self, s): print (s)

    def warning(self, s): print (s)

    def debug(self, s): print (s)

    def error(self, s): print (s)


def start_login(options, jira_env, command_name, com, logger):
    global auth
    # Attempt to recover the cached auth object, or prompt for login
    jirarc_file = jira_env['home'] + os.sep + '.jirarc'
    jira_env['jirarc_file'] = jirarc_file
    authorized = False
    while not authorized:
        try:
            logger.debug('Starting authorization')
            # Allow an explicit login, to reset the user for example
            if command_name == 'login' and os.path.exists(jirarc_file):
                os.remove(jirarc_file)
            if not os.path.exists(jirarc_file):
                logger.debug('No cached auth, starting login')
                rc = com.run('login', logger, jira_env, [options.user, options.password])
                if (rc):
                    sys.exit(rc)
            logger.debug('Reading cached auth')
            fp = open(jirarc_file, 'rb')
            jira_env['jirauser'] = fp.readline()[:-1]
            auth = fp.readline()[:-1]
            fp.close()
            # Check that the recovered auth object is still valid
            # and get some useful information at the same time
            # TODO nice to have an option to not do this to improve speed
            logger.debug('Using auth to get types')
            jira_env['types'] = soap.service.getIssueTypes(auth)
            logger.debug('Using auth to get subtask types')
            jira_env['subtypes'] = soap.service.getSubTaskIssueTypes(auth)
            logger.debug('Using auth to get statuses')
            jira_env['statuses'] = soap.service.getStatuses(auth)
            logger.debug('Using auth to get priorities')
            jira_env['priorities'] = soap.service.getPriorities(auth)
            logger.debug('Using auth to get resolutions')
            jira_env['resolutions'] = soap.service.getResolutions(auth)
            logger.debug('Using auth to get projects')
            if hasattr(soap, 'getProjects'):
                # Up to 3.12
                jira_env['projects'] = soap.service.getProjects(auth)
            else:
                jira_env['projects'] = soap.service.getProjectsNoSchemes(auth)
            authorized = True
        except KeyboardInterrupt:
            logger.info("... interrupted")
            sys.exit(0)
        except Exception, e:
            # Attempt another login
            logger.error('Previous login is invalid or has expired')
            logger.exception(e)
            if os.path.exists(jirarc_file):
                os.remove(jirarc_file)


def execute_command(options, args):
    global logger, jira_env, server, command_name, soap, home, serverInfo, rc

    com = Commands()
    logger = setupLogging(options.loglevel)
    jira_env = {}
    server = options.server + "/rpc/soap/jirasoapservice-v2?wsdl"
    # server = options.server + "/rpc/soap/sharedspace-s1v1?wsdl"
    if not server.startswith('http'):  # also catches https
        server = 'http://' + server  # default is no SSL
    if len(args) == 0 or args[0] in ['help']:
        sys.exit(com.run("help", logger, jira_env, args[1:]))
    command_name = args[0]

    if len(args) > 1 and args[1] in ['--help', '-h']:
        if com.has(command_name):
            sys.exit(com.run(command_name, logger, jira_env, args[1:]))
        else:
            sys.exit(com.run("help", logger, jira_env, args[1:]))
    elif com.has(command_name):
        try:
            logger.debug('Attempting to connect to the server: ' + server)
            soap = Client(server)
            logger.debug('Connected to the server')
            logger.debug(soap)
        except:
            logger.error('Failed to connect to: ' + server)
            sys.exit(1)

        home = "notset"
        try:
            home = os.environ['HOME']
        except KeyError:
            try:
                home = os.environ['APPDATA'] + os.sep + "JiraCLI"
            except KeyError:
                print "Warning: unable to find HOME or APPDATA to store .jirarc file"
                print "Warning: you will need to log into JIRA for every operation"
        if home != "notset" and not os.path.exists(home):
            os.makedirs(home)
        jira_env['home'] = home

        if command_name not in ['logout']:
            start_login(options, jira_env, command_name, com, logger)

        # This doesn't actually check that the session is valid
        serverInfo = soap.service.getServerInfo(auth)
        logger.debug("Server info: " + str(serverInfo))

        if (command_name not in ['login']):
            logger.debug('Running command: ' + command_name)
            rc = com.run(command_name, logger, jira_env, args[1:])
            return rc
        else:
            sys.exit(0)
    else:
        logger.error("Command '%s' not recognized." % (command_name))
        logger.error("  run '%s help' for a list of commands" % (progname))
        sys.exit(1)


if (__name__ == "__main__"):
    progname = sys.argv[0]
    parser = OptionParser(
        "usage: %prog [options] <command>\n\nRun '%prog help' for a list of commands.\nRun '%prog help -v' for a list of commands and their options",
        version="%prog 0.1")
    parser.allow_interspersed_args = False
    parser.add_option("-v", "--verbose", dest="loglevel", type="int",
                      default=logging.INFO,
                      help="Verbosity, default: %default, debug is " + str(logging.DEBUG))
    parser.add_option("-s", "--server", dest="server", default="http://jira.example.com:80",
                      help="JIRA server and port to use, default: %default")
    # parser.add_option("-p", "--project", dest="project", default="CA",
    # help="Project to use, default: %default")
    parser.add_option("-u", "--user", dest="user", default=None,
                      help="JIRA user to use, default: %default")
    parser.add_option("-p", "--password", dest="password", default=None,
                      help="JIRA password to use, default: %default")

    (options, args) = parser.parse_args()
    execute_command(options, args)

'''
suds note:

The ability to use python dict to represent complex objects was
re-introduced in 0.3.8. However, this is not the preferred method
because it may lead to passing incomplete objects. Also, this approach
has a significant limitation. Users may not use python dict for
complex objects when they are subclasses (or extensions) of types
defined in the wsdl/schema. In other words, if the schema defines a
type to be an Animal and you wish to pass a Dog (assumes Dog isa
Animal), you may not use a dict to represent the dog. In this case,
suds needs to set the xsi:type="Dog" but cannot because the python
dict does not provide enough information to indicate that it is a Dog
not an Animal. Most likely, the server will reject the request and
indicate that it cannot instantiate a abstract Animal.

'''
