import os

__all__ = ['settings']

__title__ = 'jira-service'
__version__ = '0.1'
__description__ = 'Test for JIRA SOAP API'
__url__ = 'http://www.xingshulin.com'
__author__ = 'Jack Wang'
__licence__ = 'MIT'
__copyright__ = 'Copyright 2015 Jack House'


class ConfigurationException(Exception):
    pass


CFG_PATH = os.path.join(
    os.path.dirname(__file__), 'config.ini'
)

settings = dict()

wsdl_url = username = password = None

if os.path.exists(CFG_PATH):
    from ConfigParser import SafeConfigParser

    parser = SafeConfigParser()
    parser.read(CFG_PATH)

    wsdl_url = parser.get('main', 'wsdl_url')
    project = parser.get('main', 'project')
    username = parser.get('auth', 'username')
    password = parser.get('auth', 'password')
    issue_maintenance = parser.get('issues_type', 'maintenance')
    issue_interests = parser.get('issues_type', 'interests')
    issue_product = parser.get('issues_type', 'product')
    test_summary = parser.get('test_contents', 'summary')
    test_description = parser.get('test_contents', 'description')
else:
    raise ConfigurationException(
        "Config error "
    )

if not (wsdl_url and username and password):
    raise ConfigurationException(
        "Please make sure you have configured the WSDL URL, username, and "
        "password either in your Django settings or in a config.ini file."
    )

settings['WSDL_URL'] = wsdl_url
settings['USERNAME'] = username
settings['PASSWORD'] = password
settings['PROJECT'] = project
settings['ISSUE_MNT'] = issue_maintenance
settings['ISSUE_INT'] = issue_interests
settings['ISSUE_PRD'] = issue_product
settings['TEST_SUMMARY'] = test_summary
settings['TEST_DESCRIPTION'] = test_description
