========
JIRA-RPC
========

Python client for the JIRA SOAP API.
Tested with JIRA 4.1 - 5.1 and Python 2.6 / 2.7.


Configuration
=============

First, you need to set up the configuration.
Either create a ``config.ini`` file in the ``jira`` folder, or if you're using this in a Django project, you can put the settings in your ``settings.py``, for example::

    JIRA_RPC_USER = 'abc'
    JIRA_RPC_PASS = '123'
    JIRA_WSDL_URL = 'http://jira.example.com/rpc/soap/jirasoapservice-v2?wsdl'
    JIRA_TESTING = True
    JIRA_TEST_PROJECT = 'TEST'


**WARNING** If ``TESTING`` is set to ``True``, the client connects to a project named ``TEST`` (which is assumed to exist on the server).
This is useful for testing functionality on a test project before pushing into production (maintaining an entire JIRA server just for testing seems excessive).
If you have a *real* project called ``TEST``, you should change this by overriding the test project name in the settings (see ``config.example.ini``).


Installation
============

The only requirement is ``suds``::

    pip install -r requirements.txt
