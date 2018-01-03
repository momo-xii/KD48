# -*- coding:utf-8 -*-
import os
import time
from datetime import datetime
import json
import re

def c(t):
    '''已废弃'''
    return filter_emoji(t).encode('gb18030')

def filter_emoji(desstr):
    '''
    过滤emoji表情，并转化为CoolQ的格式[CQ:emoji,id=...]
    '''
    def restr(string):
        string = string.group(0).encode('unicode-escape').decode('gb18030')
        string = int(string.replace('\\U',''), 16)
        return '[CQ:emoji,id=%d]'%string

    try:
        co = re.compile(u'[\U00010000-\U0010ffff]')
    except re.error:
        co = re.compile(u'[\uD800-\uDBFF][\uDC00-\uDFFF]')
    return co.sub(restr, desstr)

def CQfilter(string):
    '''CQ码字符转义，见https://d.cqp.me/Pro/CQ%E7%A0%81
    '''
    string = string.replace('&', '&amp;')
    string = string.replace('[', '&#91;')
    string = string.replace(']', '&#93;')
    string = string.replace(',', '&#44;')
    return string

def gbkIgnore(text):
    '''过滤非gbk符号，用于：Windows系统cmd窗口输出，CoolQ路径不支持非gbk字符'''
    return text.encode('gbk','ignore').decode('gbk','ignore')

def ISOString2Time(s):
    try:
        d = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except TypeError:
        d = datetime(*(time.strptime(s, "%Y-%m-%d %H:%M:%S")[0:6]))
    return time.mktime(d.timetuple())

ISOTime2Timestamp = ISOString2Time

def Time2ISOString(s):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(s)))

Timestamp2ISOTime = ISOString2Time

def isVaildDate(date):
    try:
        datetime.strptime(date, "%Y-%m-%d")
        return True
    except:
        return False

def isVaildTime(date):
    try:
        datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        return True
    except:
        return False

def loadJson(path):
    with open(path, encoding='utf-8') as json_file:
        data = json.load(json_file)
        return data

def saveJson(data, path):
    with open(path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, indent=4, ensure_ascii=False)

def killProcess(pid):
    os.popen('taskkill.exe /pid:'+str(pid))