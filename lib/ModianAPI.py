# -*- coding: utf-8 -*-
import os
import sys
import requests
import json
import math
import random
import glob
import sqlite3
from collections import Counter
from utility import *
from hashlib import md5
import numpy as np
from PIL import Image
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


    def getRank(self, pro_id, nickname):
        rankinfo = []
        page = 1
        while True:
            res = self.getRankingList(pro_id, _type=1, page=page)
            if res:
                find = list(filter(lambda x:x['nickname'] == nickname, res))
                if find:
                    rankinfo = find[0]
                    break
            else:
                break
            page += 1
        return rankinfo


######################### 其他功能 ##########################
    def flagCounters(self, money):
        self.flags['baseflag']['sum'] += money
        for f in self.flags:
            flag = self.flags[f]
            flag['count'] += math.floor(money/flag['level'])
            # if flag['count'] >= flag['target'] and flag['target'] != 0:
            #     flag['finish'] = 1


    def personCounters(self, order):
        self.todayLog['orderCnt'] += 1
        res = list(filter(lambda x:x['nickname'] == order['nickname'], self.todayLog['person']))
        if res:
            res[0]['money'] += order['backer_money']
        else:
            self.todayLog['person'].append({'nickname':order['nickname'], 
                'money':order['backer_money']})


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


    def loadStatus(self):
        path = os.path.join(currdir, 'config', 'modian_data.json')
        params = loadJson(path)
        self.data = params
        self.wdsLastTime = float(params['ctime'])
        self.flags['baseflag'] = params['baseflag']
        self.todayLog = params['todayLog']


    def saveStatus(self):
        path = os.path.join(currdir, 'config', 'modian_data.json')
        params = self.data
        params['ctime'] = str(self.wdsLastTime)
        params['baseflag'] = self.flags['baseflag']
        params['todayLog'] = self.todayLog
        saveJson(params, path)


class Card(object):
    def __init__(self):
        self.prob0 = [50,50,0,0]
        self.prob1 = [52,42,6,0]
        self.prob2 = [51,41,8,0]
        self.prob3 = [50,40,10,0]

    def draw(self, mode=1):
        if mode == 1:
            prob = self.prob1
        elif mode == 2:
            prob = self.prob2
        elif mode == 3:
            prob = self.prob3
        elif mode == 0:
            prob = self.prob0

        cardtype = ''
        rand = random.randint(1,sum(prob))
        if rand <= prob[0]:
            cardtype = 'N'
        elif rand <= sum(prob[0:2]):
            cardtype = 'R'
        elif rand <= sum(prob[0:3]):
            cardtype = 'SR'
        else:
            cardtype = 'SSR'
        return [cardtype, self.selectCard(cardtype)]

    def drawByType(self, cardtype):
        return [cardtype, self.selectCard(cardtype)]

    def drawByMoney(self, money):
        resCards = []
        if money == 10.7:
            resCards.append(self.draw())
        elif money == 33:
            for i in range(3):
                resCards.append(self.draw())
        elif money == 107:
            resCards.append(self.drawByType('SR'))
            cnt = 0
            while cnt < 9:
                resCards.append(self.draw(mode=2))
                cnt += 1
                c = Counter([x[0] for x in resCards])
                if c['SR'] > 3:
                    resCards.pop()
                    cnt -= 1
        elif money == 309:
            resCards.append(self.drawByType('SR'))
            if random.randint(1,100) <= 25:
                resCards.append(self.drawByType('SSR'))
                remainCnt = 28
                hasSSR = True
            else:
                remainCnt = 29
                hasSSR = False
            cnt = 0
            while cnt < remainCnt:
                resCards.append(self.draw(mode=3))
                cnt += 1
                c = Counter([x[0] for x in resCards])
                if hasSSR:
                    if c['SR'] > 3:
                        resCards.pop()
                        cnt -= 1
                else:
                    if c['SR'] > 6:
                        resCards.pop()
                        cnt -= 1
        else:
            pass
        random.shuffle(resCards)
        return resCards

    def selectCard(self, cardtype):
        imgFNs = glob.glob('../data/image/cards/%s/*.jpg'%cardtype)
        idx = random.randint(0,len(imgFNs)-1)
        return imgFNs[idx]

    def jointImgs(self, resCards):
        mkdir('../data/image/cards/synthesis/')
        longMats = []
        for i in range(len(resCards)):
            if i%5 == 0:
                baseImg = Image.open(resCards[i][1])
                baseMat = np.atleast_2d(baseImg)
            else:
                img = Image.open(resCards[i][1])
                imgMat = np.atleast_2d(img)
                baseMat = np.append(baseMat, imgMat, axis=1)
            if i%5 == 4:
                longMats.append(baseMat)
        else:
            if len(resCards)%5 != 0:
                longMats.append(baseMat)
        finalMat = longMats[0]
        for mat in longMats[1:]:
            finalMat = np.append(finalMat, mat, axis=0)
        finalImg = Image.fromarray(finalMat)
        (w,h) = finalImg.size
        if w > 1920:
            nw = 1920
            nh = int(h*(nw/w))
            finalImg = finalImg.resize((nw,nh),Image.ANTIALIAS)
        filename = '../data/image/cards/synthesis/' + str(time.time()) + '.jpg'
        finalImg.save(filename)
        return filename.lstrip('../data/image/')

    def counter(self, resCards, preCnt={'N':0,'R':0,'SR':0,'SSR':0}):
        c = Counter(preCnt)
        cardtypes = [x[0] for x in resCards]
        c.update(cardtypes)
        return c


class CardDB(object):
    def __init__(self, filename='./data/card.db'):
        self.filename = filename
        if not os.path.isfile(filename):
            self.createTable()

    def createTable(self):
        conn = sqlite3.connect(self.filename)
        cursor = conn.cursor()
        cursor.execute('''CREATE table card 
            (   nickname    varchar(50)     primary key, 
                cardcnt     text,
                orderinfo   text
            )''')
        cursor.close()
        conn.commit()
        # print("Table created successfully.")
        conn.close()

    def insert(self, nickname, cardcnt, orderinfo):
        conn = sqlite3.connect(self.filename)
        cursor = conn.cursor()
        cursor.execute('''INSERT into card 
            (nickname, cardcnt, orderinfo) values (?, ?, ?)''', 
            (nickname, cardcnt, orderinfo))
        cursor.close()
        conn.commit()
        # print("Record inserted successfully.")
        conn.close()

    def update(self, nickname, cardcnt, orderinfo):
        conn = sqlite3.connect(self.filename)
        cursor = conn.cursor()
        cursor.execute('''UPDATE card set cardcnt = ? where nickname = ?''', 
            (cardcnt, nickname))
        cursor.execute('''UPDATE card set orderinfo = ? where nickname = ?''', 
            (orderinfo, nickname))
        cursor.close()
        conn.commit()
        # print("Record updated successfully.")
        conn.close()

    def delete(self, nickname):
        conn = sqlite3.connect(self.filename)
        cursor = conn.cursor()
        cursor.execute('''DELETE from card where nickname = ?''', (nickname,))
        cursor.close()
        conn.commit()
        # print("Record deleted successfully.")
        conn.close()

    def select(self, nickname):
        conn = sqlite3.connect(self.filename)
        cursor = conn.cursor()
        cursor.execute('''SELECT * from card where nickname = ?''', (nickname,))
        values = cursor.fetchall()
        cursor.close()
        conn.close()
        return values


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
    # wds = WDS()
    # res = wds.getProjectDetail(10660)
    # res = wds.getOrders(11731, page=1, debug=False)
    # print(res)
    # res = wds.getRankingList(11731, _type=1, page=1)
    # res = wds.getRank(11731, '123')
    # print(res)
    card = Card()
    resCards = card.drawByMoney(309)
    log = '“XXX”此次抽卡结果为：\n'
    for i in range(len(resCards)):
        log += resCards[i][0] + '\t'
        log += '\n' if i%5==4 else ''
    else:
        if len(resCards)%5 != 0:
            log += '\n'
    # log += '抽到的卡牌是：\n'
    # imgFN = card.jointImgs(resCards)
    # log += imgFN
    print(log)
