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

def ISOTime2Timestamp(s):
    d = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    return d.timestamp()

ISOString2Time = ISOTime2Timestamp

def Timestamp2ISOTime(s):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(s)))

Time2ISOString = Timestamp2ISOTime

def getISODateOnly():
    return str(datetime.now()).split()[0]

def getISODateAndTime():
    return str(datetime.now()).split('.')[0]

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

def mkdir(path):
    try:
        os.makedirs(path)
    except FileExistsError:
        pass

# 从alInfo中筛选
# 筛选特定成员
def getInfoFromName(name, allInfo):
    res = list(filter(lambda x:x['memberName'] == name, allInfo))
    return res[0]

# 筛选groupId为10的成员，即SNH48的成员
def getInfoFromGroup(groupId):
    res = list(filter(lambda x:x['groupId'] == groupId, allInfo))
    return res
