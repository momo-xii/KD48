#!/use/bin/env python3

import os
import sys
import threading
import traceback

import requests
from cqsdk import RE_CQ_SPECIAL, \
    RcvdPrivateMessage, RcvdGroupMessage, RcvdDiscussMessage, \
    SendPrivateMessage, SendGroupMessage, SendDiscussMessage, \
    GroupMemberDecrease, GroupMemberIncrease
from utility import filter_emoji


CQ_ROOT = r'C:/Users/Administrator/Desktop/CQP'
CQ_IMAGE_ROOT = os.path.join(CQ_ROOT, r'data/image')


def info(*args, **kwargs):
    print("================ INFO  ================", file=sys.stderr)
    print(*args, **kwargs, file=sys.stderr)


def warning(*args, **kwargs):
    print("=============== WARNING ===============", file=sys.stderr)
    print(*args, **kwargs, file=sys.stderr)


def error(*args, **kwargs):
    print("================ ERROR ================", file=sys.stderr)
    print(*args, **kwargs, file=sys.stderr)


def match(text, keywords):
    for keyword in keywords:
        if keyword in text:
            return True
    return False


def SendPrivateMsg(qqbot, qq, text):
    text = filter_emoji(text)
    msg = SendPrivateMessage(qq=qq, text=text)
    qqbot.send(msg)


def SendPrivatesMsg(qqbot, qqs, text):
    for qq in qqs:
        SendPrivateMsg(qqbot, str(qq), text)


def SendGroupMsg(qqbot, group, text):
    text = filter_emoji(text)
    msg = SendGroupMessage(group=str(group), text=text)
    qqbot.send(msg)


def SendGroupsMsg(qqbot, groups, text):
    for group in groups:
        SendGroupMsg(qqbot, group, text)


def reply(qqbot, message, text):
    reply_msg = None
    if isinstance(message, RcvdPrivateMessage):
        reply_msg = SendPrivateMessage(
            qq=message.qq,
            text=text,
            )
    if isinstance(message, RcvdGroupMessage):
        reply_msg = SendGroupMessage(
            group=message.group,
            text=text,
            )
    if isinstance(message, RcvdDiscussMessage):
        reply_msg = SendDiscussMessage(
            discuss=message.discuss,
            text=text,
            )
    if reply_msg:
        qqbot.send(reply_msg)
        # print("↘", message)
        # print("↗", reply_msg)


class FileDownloader(threading.Thread):
    def __init__(self, url, path, requests_kwargs={}, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = url
        self.path = path
        self.requests_kwargs = requests_kwargs

    def run(self):
        try:
            self.download()
        except:
            error("[FileDownloader]", "Catch exception on downloading.")
            traceback.print_exc()

    def download(self):
        if os.path.exists(self.path):
            print("[FileDownloader]", "Exists", self.path)
            return
        r = requests.get(self.url, **self.requests_kwargs)
        with open(self.path, 'wb') as f:
            f.write(r.content)
