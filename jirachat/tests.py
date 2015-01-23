# -*- coding: utf-8 -*-
from django.test import TestCase
from jirachat.models import ServerInfo
from jirachat.views import handle_message
import string
import datetime

# Create your tests here.


class ServiceInfoTestCase(TestCase):
    # 下面这些变量均假设已由 Request 中提取完毕
    token = 'token'  # 你的微信 Token
    # signature = 'f24649c76c3f3d81b23c033da95a7a30cb7629cc'  # Request 中 GET 参数 signature
    # timestamp = '1406799650'  # Request 中 GET 参数 timestamp
    # nonce = '1505845280'  # Request 中 GET 参数 nonce
    # 用户的请求内容 (Request 中的 Body)
    # 请更改 body_text 的内容来测试下面代码的执行情况

    def setUp(self):
        ServerInfo.objects.create(signature="test_s1", timestamp="34567890", nonce="123",
                                  echostr="aaa")
        ServerInfo.objects.create(signature="test_s2", timestamp="34567895", nonce="456",
                                  echostr="bbb")

    def test_order_by(self):
        """----------------Let's do test-----------------------------"""
        serverinfos = ServerInfo.objects.order_by("timestamp").reverse()[:1]
        serverinfo = serverinfos[0]
        expecttime = "34567895"
        self.assertEqual(serverinfos.count(), 1)
        self.assertEqual(serverinfo.timestamp, expecttime)

    def test_wechat_verification_with_correct_behavior(self):
        """--------------wechat_verification_with_correct_behavior-----------"""
        body_text = """
        <xml>
        <ToUserName>user1</ToUserName>
        <FromUserName>user2</FromUserName>
        <CreateTime>1405994593</CreateTime>
        <MsgType>text</MsgType>
        <Content>wechat</Content>
        <MsgId>6038700799783131222</MsgId>
        </xml>
        """
        handle_message(body_text)

    def test_wechat_verification_with_correct_behavior(self):
        """--------------wechat_verification_with_correct_behavior-----------"""
        body_text = """
        <xml>
        <ToUserName>user1</ToUserName>
        <FromUserName>user2</FromUserName>
        <CreateTime>1405994593</CreateTime>
        <MsgType>text</MsgType>
        <Content>wechat</Content>
        <MsgId>6038700799783131222</MsgId>
        </xml>
        """
        resp_text = handle_message(body_text).encode('utf-8').replace(" ", "").replace("\n", "")
        self.assertNotEqual(resp_text, "")

    def test_should_swipe_user_in_response(self):
        """--------------correct response-----------"""
        body_text = """
        <xml>
        <ToUserName>user1</ToUserName>
        <FromUserName>user2</FromUserName>
        <CreateTime>1405994593</CreateTime>
        <MsgType>text</MsgType>
        <Content>wechat</Content>
        <MsgId>6038700799783131222</MsgId>
        </xml>
        """
        resp_text = handle_message(body_text).encode('utf-8').replace(" ", "").replace("\n", "")

        expect_user1 = "<FromUserName><![CDATA[user1]]></FromUserName>"
        expect_user2 = "<ToUserName><![CDATA[user2]]></ToUserName>"
        self.assertEqual(expect_user1 in resp_text, True)
        self.assertEqual(expect_user2 in resp_text, True)
