from django.test import TestCase
from jirachat.models import ServerInfo
import datetime

# Create your tests here.


class ServiceInfoTestCase(TestCase):
    def setUp(self):
        ServerInfo.objects.create(signature="test_s1", timestamp=datetime.datetime(2014, 10, 31), nonce="123",
                                  echostr="aaa")
        ServerInfo.objects.create(signature="test_s2", timestamp=datetime.datetime(2014, 12, 24), nonce="456",
                                  echostr="bbb")

    def test_order_by(self):
        """----------------Let's do test-----------------------------"""
        serverinfos = ServerInfo.objects.order_by("timestamp").reverse()[:1]
        serverinfo = serverinfos[0]
        serverinfo_timestamp = serverinfo.timestamp.replace(tzinfo=None)
        expecttime = datetime.datetime(2014, 12, 24)

        self.assertEqual(serverinfos.count(), 1)
        self.assertEqual(serverinfo_timestamp, expecttime)