# -*- coding: utf-8 -*-
from django.views.decorators.csrf import csrf_exempt

import datetime
from wechat_sdk import WechatBasic
from django.shortcuts import render_to_response
from django.http import HttpResponse
from .models import Line
from .models import ServerInfo


token = 'token'  # 你的微信 Token


# Create your views here.
def home(request):
    return render_to_response("jirachat/home.html", {'lines': Line.objects.all()})


@csrf_exempt
def wechat(request):
    if request.method == 'GET':
        wechatserviceinfo = request.GET
        echostr = init_service(wechatserviceinfo)
        return HttpResponse(echostr)
    elif request.method == 'POST':
        body_text = request.body
        resp_text = handle_message(body_text)
        print(resp_text)
    return render_to_response("jirachat/wechat.html", {'infos': ServerInfo.objects.order_by("timestamp").reverse()[:1]})


def init_service(wechatserviceinfo):
    wechatsignature = wechatserviceinfo.get('signature', '')
    wechattimestamp = wechatserviceinfo.get('timestamp', '')
    wechatnonce = wechatserviceinfo.get('nonce', '')
    wechatechostr = wechatserviceinfo.get('echostr', '')
    create_service_info(wechatsignature, wechattimestamp, wechatnonce, wechatechostr)
    return wechatechostr


def get_last_service_info():
    return ServerInfo.objects.order_by("timestamp").reverse()[0]


def handle_text_message(message, resp, wechat):
    if message.content == 'wechat':
        resp = wechat.response_text(u'^_^')
    else:
        resp = wechat.response_text(u'文字')
    return resp


def handle_message(body_text):
    # 实例化 wechat
    wechat = WechatBasic(token=token)

    # 对签名进行校验
    # serviceinfo = get_last_service_info()
    # if not (wechat.check_signature(signature=serviceinfo.signature, timestamp=serviceinfo.timestamp,
    # nonce=serviceinfo.nonce)):
    # return

    # 对 XML 数据进行解析 (必要, 否则不可执行 response_text, response_image 等操作)
    wechat.parse_data(body_text)
    # 获得解析结果, message 为 WechatMessage 对象 (wechat_sdk.messages中定义)
    message = wechat.get_message()
    resp = None
    if message.type == 'text':
        resp = handle_text_message(message, resp, wechat)
    elif message.type == 'image':
        resp = wechat.response_text(u'图片')
    else:
        resp = wechat.response_text(u'未知')
    return resp


def create_service_info(signature='signation', timestamp="00000001", nonce="3456789", echostr="ertyui"):
    info = ServerInfo(signature=signature, timestamp=timestamp, nonce=nonce, echostr=echostr)
    info.save()

