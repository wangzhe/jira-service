# -*- coding: utf-8 -*-
from django.views.decorators.csrf import csrf_exempt

import datetime
from wechat_sdk import WechatBasic
from django.shortcuts import render_to_response
from django.http import HttpResponse
from .models import Line
from .models import ServerInfo



# 下面这些变量均假设已由 Request 中提取完毕
token = 'token'  # 你的微信 Token
# signature = 'f24649c76c3f3d81b23c033da95a7a30cb7629cc'  # Request 中 GET 参数 signature
# timestamp = '1406799650'  # Request 中 GET 参数 timestamp
# nonce = '1505845280'  # Request 中 GET 参数 nonce
# 用户的请求内容 (Request 中的 Body)
# 请更改 body_text 的内容来测试下面代码的执行情况
body_text = """
<xml>
<ToUserName><![CDATA[touser]]></ToUserName>
<FromUserName><![CDATA[fromuser]]></FromUserName>
<CreateTime>1405994593</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[wechat]]></Content>
<MsgId>6038700799783131222</MsgId>
</xml>
"""


# Create your views here.
def home(request):
    return render_to_response("jirachat/home.html", {'lines': Line.objects.all()})


@csrf_exempt
def wechat(request):
    if request.method == 'GET':
        echostr = init_service(request)
        return HttpResponse(echostr)
    elif request.method == 'POST':
        handle_message(request)
    return render_to_response("jirachat/wechat.html", {'infos': ServerInfo.objects.order_by("timestamp").reverse()[:1]})


def init_service(request):
    wechatserviceinfo = request.GET
    wechatsignatur = wechatserviceinfo.get('signature', '')
    wechattimestamp = wechatserviceinfo.get('timestamp', '')
    wechatnonce = wechatserviceinfo.get('nonce', '')
    wechatechostr = wechatserviceinfo.get('echostr', '')
    print (wechatsignatur, wechattimestamp, wechatnonce, wechatechostr)
    # create_service_info(wechatsignatur, wechattimestamp, wechatnonce, wechatechostr)
    return wechatechostr


def get_last_service_info():
    return ServerInfo.objects.order_by("timestamp").reverse()[:1]


def handle_message(request):
    # 实例化 wechat
    wechat = WechatBasic(token=token)
    wechatserviceinfo = get_last_service_info()
    if wechatserviceinfo.size != 0:
        print wechatserviceinfo.timestamp

    # 对签名进行校验
    # if wechat.check_signature(signature=signature, timestamp=timestamp, nonce=nonce):
    # # 对 XML 数据进行解析 (必要, 否则不可执行 response_text, response_image 等操作)
    #     wechat.parse_data(body_text)
    #     # 获得解析结果, message 为 WechatMessage 对象 (wechat_sdk.messages中定义)
    #     message = wechat.get_message()
    #
    #     response = None
    #     if message.type == 'text':
    #         if message.content == 'wechat':
    #             response = wechat.response_text(u'^_^')
    #         else:
    #             response = wechat.response_text(u'文字')
    #     elif message.type == 'image':
    #         response = wechat.response_text(u'图片')
    #     else:
    #         response = wechat.response_text(u'未知')
    #
    #     # 现在直接将 response 变量内容直接作为 HTTP Response 响应微信服务器即可，此处为了演示返回内容，直接将响应进行输出
    #     print response
    return


def create_service_info(signature='signation', timestamp=datetime.datetime.now(), nonce="3456789", echostr="ertyui"):
    info = ServerInfo(signature=signature, timestamp=timestamp, nonce=nonce, echostr=echostr)
    info.save()

