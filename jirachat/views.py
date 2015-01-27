# -*- coding: utf-8 -*-
from django.views.decorators.csrf import csrf_exempt
from wechat_sdk import WechatBasic
from django.shortcuts import render_to_response
from django.http import HttpResponse

from .models import Line
from .models import ServerInfo
from module import constants
from module.message import build_text_handler


token = 'token'  # 你的微信 Token


# Create your views here.
def home(request):
    return render_to_response("jirachat/home.html", {'lines': Line.objects.all()})


@csrf_exempt
def wechat(request):
    if request.method == 'GET':
        wechatserviceinfo = request.GET
        resp_text = init_service(wechatserviceinfo)
    elif request.method == 'POST':
        body_text = request.body
        resp_text = handle_message(body_text)
        print(resp_text)
    return HttpResponse(resp_text)


def init_service(wechatserviceinfo):
    wechatnonce, wechatsignature, wechattimestamp = wechat_get_paramaters(wechatserviceinfo)
    wechatechostr = wechatserviceinfo.get('echostr', '')
    create_service_info(wechatsignature, wechattimestamp, wechatnonce, wechatechostr)
    return wechatechostr


def handle_message(body_text):
    wechat = WechatBasic(token=token)
    # 对签名进行校验
    # wechatnonce, wechatsignature, wechattimestamp = wechat_get_paramaters(wechatserviceinfo)
    # if not (wechat.check_signature(signature=wechatsignature, timestamp=wechattimestamp, nonce=wechatnonce)):
    #     return
    wechat.parse_data(body_text)
    message = wechat.get_message()
    try:
        message_handler = build_handler(message)
        resp_content = message_handler.process(message.content)
    except Exception, e:
        resp_content = constants.sys_err
        print e
    return wechat.response_text(resp_content)


def wechat_get_paramaters(wechatserviceinfo):
    wechatsignature = wechatserviceinfo.get('signature', '')
    wechattimestamp = wechatserviceinfo.get('timestamp', '')
    wechatnonce = wechatserviceinfo.get('nonce', '')
    return wechatnonce, wechatsignature, wechattimestamp


def get_last_service_info():
    return ServerInfo.objects.order_by("timestamp").reverse()[0]


def handle_text_message(message, wechat):
    if message.content == 'wechat':
        resp = wechat.response_text(u'^_^')
    else:
        resp = wechat.response_text(u'文字')
    return resp


def create_service_info(signature='signature', timestamp="00000001", nonce="3456789", echostr="ertyui"):
    info = ServerInfo(signature=signature, timestamp=timestamp, nonce=nonce, echostr=echostr)
    info.save()


def build_handler(message):
    # build handler according to type and content
    handler = None
    if message.type == 'text':
        handler = build_text_handler(message.content)
    elif message.type == 'image':
        handler = build_text_handler(message.content)
    else:
        pass
    return handler
