# -*- coding: utf-8 -*-
import os
import sys
import requests
import json
import math
from utility import *
from hashlib import md5
from configparser import ConfigParser
import urllib.request as request
import logging

currdir = '.' #os.path.abspath(os.path.dirname(__file__))

class WDS(object):
    def __init__(self):
        self.wdss = requests.Session()
        self.wdsLastTime = 0
        self.flags = {}


    def getHeader(self):
        header = {}
        # header['device'] = 'SM919'
        # header['sdk'] = '23'
        # header['imei'] = '990029904632033'
        # header['client'] = '2'
        # header['version'] = '2.1.5'
        # header['channel'] = 'chuizi'
        # header['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
        header['User-Agent'] = 'Dalvik/2.1.0 (Linux; U; Android 6.0.1; SM919 Build/MXB48T)'
        # header['Host'] = 'wds.modian.com'
        # header['Connection'] = 'Keep-Alive'
        # header['Accept-Encoding'] = 'gzip'
        return header


    def getSign(self, data, P='das41aq6'):
        string = ""
        sortedKeys = sorted(data.keys())
        for k in sortedKeys:
            value = data[k]
            if value == "" or value is None:
                continue
            string += str(k)
            string += "="
            string += str(value)
            string += "&"
        string += "p="+P
        m = md5()
        m.update(string.encode('utf8'))
        md5str = m.hexdigest()
        return md5str[5:21]


    def getProjectDetail(self, pro_id):
        '''
        获取摩点集资项目信息
        pro_id: 网页网址最后的数字id
        '''
        url = 'https://wds.modian.com/api/project/detail'
        data = {'pro_id':pro_id}
        sign = self.getSign(data)
        data['sign'] = sign

        try:
            res = self.wdss.request('POST', url, headers=self.getHeader(), data=data)
            j = res.json()
        except Exception as e:
            logging.exception(e)
            return None

        if j['status'] == '2':
            logging.error(j['message'])
            return None
        elif j['status'] == '0':
            # succeed
            pass
        else:
            logging.error('Unknown error.')
            return None

        wdsInfo = j['data'][0]
        # "pro_id":"10250",
        # "pro_name":"【陪你远征，伴你同行】2018宮脇咲良总选举应援",
        # "goal":"31900",
        # "already_raised":2101,
        # "end_time":"2018-01-01 03:19:00",
        # "pc_cover":"https://p.moimg.net/bbs_attachments/2017/12/11/20171211_1512945825_3643.jpg",
        # "mobile_cover":"https://p.moimg.net/bbs_attachments/2017/12/11/20171211_1512945825_6800.jpg"
        wdsInfo['moxi_id'] = wdsInfo['pro_id']
        wdsInfo['targetMoney'] = wdsInfo['goal']
        wdsInfo['currMoney'] = wdsInfo['already_raised']
        wdsInfo['topic'] = wdsInfo['pro_name']
        # wdsInfo['num_people'] = info['pay_count']
        # wdsInfo['start_time'] = info['start_time']
        wdsInfo['end_time'] = wdsInfo['end_time']
        return wdsInfo


    def getOrders(self, pro_id, page=1, debug=False):
        '''
        获取摩点实时集资列表
        '''
        url = 'https://wds.modian.com/api/project/orders'
        data = {'page':page, 'pro_id':pro_id}
        sign = self.getSign(data)
        data['sign'] = sign
        wdsInfo = []
        try:
            res = self.wdss.request('POST', url, headers=self.getHeader(), data=data)
            j = res.json()
        except Exception as e:
            logging.exception(e)
            return wdsInfo

        if j['status'] == '2':
            logging.error(j['message'])
            return wdsInfo
        elif j['status'] == '0':
            # succeed
            pass
        else:
            logging.error('Unknown error.')
            return wdsInfo
        
        orderList = j['data']
        for order in orderList:
            order['timpstamp'] = ISOString2Time(order['pay_time'])
        orderList.sort(key=lambda x:(-x['timpstamp']))
        for order in reversed(orderList):
            ctime = ISOString2Time(order['pay_time'])
            if self.wdsLastTime < ctime or debug:
                # "nickname":"一个冰锐",
                # "pay_time":"2017-12-12 23:24:22",
                # "backer_money":3.19
                wdsInfo.append(order)
        if len(orderList) > 0:
            self.wdsLastTime = ISOString2Time(orderList[0]['pay_time'])
        return wdsInfo


    def getRankingList(self, pro_id, _type=1, page=1):
        '''
        获取集资排行榜
        '''
        url = 'https://wds.modian.com/api/project/rankings'
        data = {'page':page, 'pro_id':pro_id, 'type':_type}
        sign = self.getSign(data)
        data['sign'] = sign
        try:
            res = self.wdss.request('POST', url, headers=self.getHeader(), data=data)
            j = res.json()
        except Exception as e:
            logging.exception(e)
            return None

        if j['status'] == '2':
            logging.error(j['message'])
            return None
        elif j['status'] == '0':
            # succeed
            pass
        else:
            logging.error('Unknown error.')
            return None

        # 集资榜
        # "nickname":"F_ic",
        # "rank":1,
        # "backer_money":"319.00"
        # 打卡榜
        # "nickname":"这是你的白熊吗",
        # "rank":1,
        # "support_days":3
        rankList = j['data']
        return rankList



######################### 其他功能 ##########################
    def flagCounters(self, money):
        for f in self.flags:
            flag = self.flags[f]
            flag['count'] += math.floor(money/flag['level'])
            # if flag['count'] >= flag['target'] and flag['target'] != 0:
            #     flag['finish'] = 1


    def loadNewFlag(self):
        path = os.path.join(currdir,'config','newflag.ini')
        config = ConfigParser()
        config.readfp(open(path))
        if config.getint("newflag","loaded") == 1:
            return None

        newflag = {}
        name = config.get("newflag","name")
        newflag['level'] = config.getfloat("newflag","level")
        newflag['target'] = config.getint("newflag","target")
        newflag['count'] = config.getint("newflag","count")
        if newflag['count'] >= newflag['target'] and newflag['target'] != 0:
            newflag['finish'] = 1
        else:
            newflag['finish'] = 0

        self.flags[name] = newflag
        config.set('newflag', 'loaded', '1')
        config.write(open(path, 'w'))


    def saveFlags(self): #to be deleted
        path = os.path.join(currdir,'config','flagStatus.ini')
        config = ConfigParser()
        for f in self.flags:
            flag = self.flags[f]
            config.add_section(f)
            config.set(f, 'level', str(flag['level']))
            config.set(f, 'target', str(flag['target']))
            config.set(f, 'count', str(int(flag['count'])))
            # config.set(f, 'ctime', str(flag['ctime']))
        config.write(open(path, 'w'))


    def loadFlags(self): #to be deleted
        path = os.path.join(currdir,'config','flagStatus.ini')
        config = ConfigParser()
        config.readfp(open(path))
        names = config.sections()
        for name in names:
            flag = {}
            flag['level'] = config.getfloat(name, 'level')
            flag['target'] = config.getint(name, 'target')
            flag['count'] = config.getint(name, 'count')
            if flag['count'] >= flag['target'] and flag['target'] != 0:
                flag['finish'] = 1
            else:
                flag['finish'] = 0
            self.flags[name] = flag


    def delFlag(self, name):  # TODO
        if name in self.flags.keys():
            self.flags.pop(name)


    def loadStatus(self):
        path = os.path.join(currdir, 'config', 'modian_data.json')
        params = loadJson(path)
        self.wdsLastTime = float(params['ctime'])
        flag = {}
        flag['level'] = params['baseflag']['level']
        flag['count'] = params['baseflag']['count']
        flag['date'] = params['baseflag']['date']
        if flag['date'] != getISODateOnly():
            flag['count'] = 0
            flag['date'] = getISODateOnly()
        self.flags['baseflag'] = flag
        self.todayLog = params['todayLog']


    def saveStatus(self):
        path = os.path.join(currdir, 'config', 'modian_data.json')
        params = loadJson(path)
        params['ctime'] = str(self.wdsLastTime)
        params['baseflag'] = self.flags['baseflag']
        params['todayLog'] = self.todayLog
        saveJson(params, path)


class PrintFlag(object):
    def __init__(self):
        self.path = os.path.join(currdir,'config', 'flag.json')

    def load(self):
        self.txt = loadJson(self.path)

    def getMessage(self):
        self.load()
        return self.txt


class Egg(object):
    def __init__(self):
        self.path = os.path.join(currdir,'config', 'eggs.ini')
        self.config = ConfigParser()
        self.eggs = {}

    def load(self):
        self.config.readfp(open(self.path))
        eggMoney = self.config.sections()
        for e in eggMoney:
            egg = {}
            egg['name'] = self.config.get(e, 'name')
            egg['msg'] = self.config.get(e, 'msg')
            self.eggs[float(e)] = egg


if __name__ == "__main__":
    wds = WDS()
    res = wds.getProjectDetail(10660)
    print(res)
    re = wds.getOrders(10660, page=1)
    print(re)
