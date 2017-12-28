# -*- coding:utf-8 -*-
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

def gbkIgnore(text):
    '''Windows系统cmd窗口输出时，过滤非gbk符号'''
    return text.encode('gbk','ignore').decode('gbk','ignore')

def ISOString2Time(s):
    try:
        d = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except TypeError:
        d = datetime(*(time.strptime(s, "%Y-%m-%d %H:%M:%S")[0:6]))
    return time.mktime(d.timetuple())

def Time2ISOString(s):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(s)))

def loadJson(path):
    with open(path, encoding='utf-8') as json_file:
        data = json.load(json_file)
        return data

def saveJson(data, path):
    with open(path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, indent=4, ensure_ascii=False)
