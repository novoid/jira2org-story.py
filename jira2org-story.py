#!/usr/bin/env python
# -*- coding: utf-8 -*-
PROG_VERSION = u"Time-stamp: <2016-05-13 14:00:47 karl.voit>"

import sys
import os
import re
import argparse
import time

CONFIGDIR = os.getcwdu()
CONFIGFILEBASENAME = 'jiraconfig'
CONFIGFILENAME = os.path.join(CONFIGDIR, CONFIGFILEBASENAME)
CONFIGTEMPLATE = '''
JIRA_USER = 'joe'
JIRA_PASSWORD = 'secret password for me'
'''

DESCRIPTION = u'''This tool retrieves a Jira issue and returns an Org-mode
representation according to the system of Karl Voit.

The output is highly specific for my personal usage. If you want to have
a similar functionality, you have to adapt it to your needs. This would
require at least a search&replace of "IPD" with the Jira project ID of
your choice, all Jira URLs, and the custom org-mode link "ipd:1234".
'''

EPILOG=u'''autor:      Karl Voit <tools@Karl-Voit.at>
license:    GPL v3 or any later version
URL:        https://github.com/novoid/FIXXME/
bugreports: via GitHub
version:    ''' + PROG_VERSION + '\n'

parser = argparse.ArgumentParser(description=DESCRIPTION,
                                 epilog=EPILOG,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)

parser.add_argument('IPD', nargs='+', help='One or many IPD numbers of stories or epics (without \"IPD-\" prefix)')

verbosity_group = parser.add_mutually_exclusive_group()
##verbosity_group.add_argument("--verbose", action="store_true")
##verbosity_group.add_argument("--quiet", action="store_true")
verbosity_group.add_argument('--version', action='version', version=PROG_VERSION)

args = parser.parse_args()

output_text = u''  # global output string for all stdout/file output operations

def print_line(text):
    global output_text
    output_text += text + '\n'
    print text

def print_item(ipd, message, level=1, empty_checkbox=False, filled_checkbox=False, omit_print=False):
    currentprefix = OUTPUTPREFIX + (level - 1) * u'  '
    text = currentprefix + '- '
    if empty_checkbox:
        text += '[ ] '
    elif filled_checkbox:
        #text += '[X] '
        text += ''
    if ipd:
        text += orglink(ipd) + ' '
    text += message
    if omit_print:
        return text
    else:
        print_line(text)


def thing2string(data, addlink=False):
    "simplify a set (or list) like (['foo', 'bar']) to 'foo, bar'"

    if len(data) < 1:
        return ''

    result = ''
    for item in data:
        if addlink:
            result += orglink(item) + ' '
        else:
            result += item + ', '
    if addlink:
        return result[:-1]
    else:
        return result[:-2]


def orglink(text):
    "Takes a text like 'IPD-1234' and generates an Org-mode link"

    return '[[' + text.replace('IPD-', 'https://product.infonova.at/jira/browse/IPD-') + '][' + text.replace('IPD-', '') + ']]'


def get(issues, ipd, query):

    return issues[ipd][query]

def extract_issue_fields(issue):

    if issue.fields.customfield_10607:
        team = issue.fields.customfield_10607.value.encode('latin-1', 'ignore')
    else:
        team = None

    if issue.fields.assignee:
        assignee = issue.fields.assignee.name.encode('latin-1', 'ignore')
        assigneelong = issue.fields.assignee.displayName.encode('latin-1', 'ignore')
    else:
        assignee = None
        assigneelong = None

    if not issue.fields.customfield_11800:
        ghsprint = None
    else:
        ghsprint = re.sub(r'.+name=(.+?),.+$', r'\1', issue.fields.customfield_11800[0]),

    return {'key': issue.key[4:],
            'fix_versions': [x.name for x in issue.fields.fixVersions],
            'created': issue.fields.created,
            'description': issue.fields.description,
            'issuetype': issue.fields.issuetype.name,
            'labels': issue.fields.labels,
            'assigneelong': assigneelong,
            'assignee': assignee,
            'reporter': issue.fields.reporter.displayName,
            'resolution': issue.fields.resolution,
            'resolutiondate': issue.fields.resolutiondate,
            'status': issue.fields.status.name,
            'summary': issue.fields.summary.encode('latin-1', 'ignore'),
            'ghsprint': ghsprint,
            'team': team,
            'priority': issue.fields.priority.name,
            'affects_versions': [x.name for x in issue.fields.versions]
    }



def retrieve_data_from_jira(ipds):

    try:
        sys.path.insert(0, CONFIGDIR)  # add cwd to Python path in order to find config file
        import jiraconfig  # here, I was not able to use the CONFIGFILENAME variable
    except ImportError:
        print "\nERROR: Could not find \"" + CONFIGFILENAME + \
            "\".\nPlease generate such a file in the " + \
            "same directory as this script with following content and configure accordingly:\n" + \
            CONFIGTEMPLATE
        sys.exit(11)

    try:
        from jira import JIRA
    except ImportError:
        print_line("ERROR: Could not find Python module \"JIRA\".\nPlease install it, e.g., with \"sudo pip install jira\".")
        sys.exit(12)

    jira = JIRA('https://product.infonova.at/jira/', basic_auth=(jiraconfig.JIRA_USER, jiraconfig.JIRA_PASSWORD))

    query = 'key = "IPD-' + '" or key = "IPD-'.join(ipds) + '" ORDER BY key'
    queryissues = jira.search_issues(query)

    issues = []
    for issue in queryissues:

        if issue.fields.issuetype.name == u'Epic':
            ## if it is an Epic, query for its stories instead
            epicquery = 'project = ipd and type = Story and "Epic Link" = ' + issue.key + ' ORDER BY key'
            #print 'DEBUG: found epic, query=[' + epicquery + ']'
            epicissues = jira.search_issues(epicquery)
            issues.extend(retrieve_data_from_jira([x.key.replace('IPD-', '') for x in epicissues]))

        elif issue.fields.issuetype.name == u'Story':
            #print 'DEBUG: found story'
            issues.append(extract_issue_fields(issue))

        else:
            ## report Defects and so forth
            print_line(u'ERROR: IPD-' + issue.key + ' is a ' + issue.fields.issuetype.name + \
                       '. Only Stories and Epics are handled here.')
            sys.exit(13)

    return issues

def print_issue(issue):

    orgdate = time.strftime("%Y-%m-%d", time.localtime())
    orgtime = time.strftime("%Y-%m-%d %H:%M", time.localtime())
    DEFAULTSHORT = 'i' + issue['key']
    short = DEFAULTSHORT

    print_line(u'')
    #print_item(None, u'Query time: ' + query_time)
    print_line(u'''
** TODO [[IPD:''' + issue['''key'''] + ''']] ''' + issue['''summary'''] + \
               ''' [0/7]                   :US_''' + short + ''':
:PROPERTIES:
:CREATED:  [''' + orgtime + ''']
:ID: ''' + orgdate + '''-Story-''' + short)
    print_line(u''':END:

 | *IPD* | *Confluence* | *Champ* |''')

    if issue['''assignee''']:
        champ = issue['''assignee''']
    else:
        champ = '''-'''

    print_line(u''' | [[IPD:''' + issue['''key'''] + '''][''' + issue['''key'''] + ''']]  | ''' + \
               issue['''summary'''] + ''' | ''' + champ + ''' |

*** STARTED create Jira [[IPD:%s]]''' % issue['''key'''])
    print_line(u''':PROPERTIES:
:CREATED:  [''' + orgtime + ''']
:ID: ''' + orgdate + '''-''' + short + '''-create-jira-ipd
:BLOCKER:
:TRIGGER:  ''' + orgdate + '''-''' + short + '''-define-champ(NEXT) ''' + \
               orgdate + '''-''' + short + '''-estimation(NEXT)
:END:

- fill out:
  - [X] set reporter
  - [ ] set level red
  - [ ] fixVersion

*** NEXT create Confluence page with template
SCHEDULED: <''' + orgdate + '''>
:PROPERTIES:
:CREATED:  [''' + orgtime + ''']
:ID:    ''' + orgdate + '''-''' + short + '''-create-confluence-page
:BLOCKER:
:TRIGGER:  ''' + orgdate + '''-''' + short + '''-write-acceptance-criteria(NEXT)
:END:

- fill out:
  - [ ] add Jira-Link [[IPD:''' + issue['''key'''] + ''']]
  - [ ] PO
  - [ ] Title
  - [ ] Business Value
- [ ] add Confluence-short-URL to story table above

*** TODO write Acceptance Criteria, Docu, Perms
:PROPERTIES:
:CREATED:  [''' + orgtime + ''']
:ID: ''' + orgdate + '''-''' + short + '''-write-acceptance-criteria
:BLOCKER: ''' + orgdate + '''-''' + short + '''-create-confluence-page
:TRIGGER: ''' + orgdate + '''-''' + short + '''-confidence-green(NEXT) ''' + \
               orgdate + '''-''' + short + '''-hand-over-team(NEXT)
:END:

*** TODO add Champ to Confluence and Jira                                    :refinement:
:PROPERTIES:
:CATEGORY: refinement
:CREATED:  [''' + orgtime + ''']
:ID: ''' + orgdate + '''-''' + short + '''-define-champ
:BLOCKER:
:END:

*** TODO get Estimation on [[IPD:''' + issue['''key'''] + \
               ''']]                                           :refinement:
:PROPERTIES:
:CREATED:  [''' + orgtime + ''']
:CATEGORY: refinement
:ID: ''' + orgdate + '''-''' + short + '''-estimation
:BLOCKER: ''' + orgdate + '''-''' + short + '''-create-jira-ipd
:TRIGGER:
:END:

- Estimation:

*** TODO get confidence-level green on [[IPD:''' + issue['''key'''] + \
               ''']]                                :refinement:
:PROPERTIES:
:CATEGORY: refinement
:CREATED:  [''' + orgtime + ''']
:ID: ''' + orgdate + '''-''' + short + '''-confidence-green
:BLOCKER: ''' + orgdate + '''-''' + short + '''-write-acceptance-criteria ''' + \
               orgdate + '''-''' + short + '''-estimation
:TRIGGER:
:END:

*** TODO hand over to team
:PROPERTIES:
:CREATED:  [''' + orgtime + ''']
:BLOCKER: ''' + orgdate + '''-''' + short + '''-write-acceptance-criteria ''' + \
               orgdate + '''-''' + short + '''-estimation
:ID: ''' + orgdate + '''-''' + short + '''-hand-over-team
:TRIGGER:  ''' + orgdate + '''-''' + short + '''-accept(WAITING) ''' + \
               orgdate + '''-Story-''' + short + '''(TEAM)
:END:

*** acceptance + finish US
:PROPERTIES:
:CREATED:  [''' + orgtime + ''']
:ID: ''' + orgdate + '''-''' + short + '''-accept
:BLOCKER: ''' + orgdate + '''-''' + short + '''-hand-over-team
:TRIGGER: ''' + orgdate + '''-Story-''' + short + '''(DONE)
:END:
''')


def main():
    """Main function"""

    ipds = []
    for argument in args.IPD:
        for ipd in argument.split(' '):
            ## maybe, there is only one argument like "1234 2345" which needs to be splitted:
            ipd_int = int(ipd)
            ipds.append(str(ipd_int))  # make sure that there are only numbers

    issues = retrieve_data_from_jira(ipds)

    for issue in issues:
        print_issue(issue)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:

        logging.info("Received KeyboardInterrupt")

# END OF FILE #################################################################
