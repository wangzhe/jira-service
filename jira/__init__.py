import os

__all__ = ['settings']

__title__ = 'jira'
__version__ = '0.1'
__description__ = 'Python client for JIRA SOAP API'
__url__ = 'https://github.com/Maplecroft/jira-rpc'
__author__ = 'James Rutherford'
__licence__ = 'MIT'
__copyright__ = 'Copyright 2012 Maplecroft'


class ConfigurationException(Exception):
    pass


CFG_PATH = os.path.join(
    os.path.dirname(__file__), 'config.ini'
)

settings = dict()

wsdl_url = username = password = None
testing = False
test_project = 'TEST'

if os.path.exists(CFG_PATH):
    from ConfigParser import SafeConfigParser

    parser = SafeConfigParser()
    parser.read(CFG_PATH)

    wsdl_url = parser.get('main', 'wsdl_url')
    testing = parser.getboolean('main', 'testing')
    test_project = parser.get('main', 'test_project')
    username = parser.get('auth', 'username')
    password = parser.get('auth', 'password')
else:
    try:
        from django.conf import settings as django_settings
        try:
            testing = django_settings.JIRA_TESTING
        except AttributeError:
            pass

        try:
            test_project = django_settings.JIRA_TEST_PROJECT
        except AttributeError:
            pass

        wsdl_url = django_settings.JIRA_WSDL_URL
        username = django_settings.JIRA_RPC_USER
        password = django_settings.JIRA_RPC_PASS
    except:
        pass

if not (wsdl_url and username and password):
    raise ConfigurationException(
        "Please make sure you have configured the WSDL URL, username, and "
        "password either in your Django settings or in a config.ini file."
    )

settings['WSDL_URL'] = wsdl_url
settings['USERNAME'] = username
settings['PASSWORD'] = password
settings['TESTING'] = testing
settings['TEST_PROJECT'] = test_project
