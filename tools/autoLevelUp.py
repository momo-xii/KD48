# -*- coding:utf-8 -*-
# 自动打卡、分享直播涨经验
import sys
import time
import logging
from apscheduler.schedulers.blocking import BlockingScheduler

sys.path.append('../lib')
from KD48API import KD48API
from utility import *
import mylog
mylog.setLog('autoLevelUp', logging.WARNING)

# setting
root = '../'
SLEEPTIME = 5
accountFN = root + 'data/account/pocket48.txt'
tempData = root + 'data/account/weiboId.json'

def loadAccountFromTxt(fn, splitMark=''):
    # fn - 文件名，文件内每个账号密码一行
    # splitMark - 账号和密码之间的间隔符，默认为空格
    accounts = []
    with open(fn,'r',encoding='utf-8-sig') as f:
        line = f.readline()
        while line:
            if splitMark == '':
                params = line.strip().split()
            else:
                params = line.strip().split(splitMark)
            currAcc = {}
            if len(params) == 2:
                currAcc['account'] = params[0]
                currAcc['password'] = params[1]
                currAcc['type'] = 'phone'
            elif len(params) == 3:
                currAcc['account'] = params[0]
                currAcc['password'] = params[1]
                currAcc['type'] = params[2]
            else:
                print('Error 账号信息有误：%s'%(line))
                continue
            
            accounts.append(currAcc)
            line = f.readline()
    return accounts


def getCurrExp(token, userId):
    res = api.getUserInfo(token, userId)
    while res['status'] < 0:
        print(res['msg'])
        time.sleep(SLEEPTIME)
        res = api.getUserInfo(token, userId)
    exp = res['data']['experience']
    return exp


def levelUp(token, userId):
    # 当前日期
    today = time.strftime("%Y-%m-%d", time.localtime(time.time()))
    print(today)

    # 当前经验值
    expBefore = getCurrExp(token, userId)
    print('当前经验值：', expBefore)

    # 分享直播2次
    res = api.getLiveList(token)
    while res['status'] < 0:
        print(res['msg'])
        time.sleep(SLEEPTIME)
        res = api.getLiveList(token)
    time.sleep(SLEEPTIME)
    reviewList = res['reviewList']
    liveId = reviewList[0]['liveId']

    succCnt = 0
    while succCnt < 2:
        res = api.shareLive(token, userId, liveId)
        print(res['msg'])
        if res['status'] != -1:
            succCnt += 1
        time.sleep(SLEEPTIME)

    # 点赞微博5次
    # TODO: 检测当日已点赞次数，给每个号生成独自的IMEI号并保存
    weiboData = loadJson(tempData)
    weiboId = weiboData['weiboId']
    succCnt = 0
    noExpCnt = 0
    faildCnt = 0
    while(True):
        weiboId += 1
        print('weiboId:', weiboId)
        res = api.praiseWeibo(token, weiboId)
        if res['status'] < 0:
            print(res['msg'])
            time.sleep(SLEEPTIME)
            faildCnt += 1
            if faildCnt < 3:
                weiboId -= 1
            else:
                faildCnt = 0
            continue
        else:
            faildCnt = 0
        if res['data']['exp'] == 1:
            succCnt += 1
            print(res['msg'], '%d次'%succCnt)
        else:
            print('点赞没加经验')
            noExpCnt += 1
            # weiboId -= 1
            # break
        time.sleep(SLEEPTIME)

        if succCnt >= 5 or noExpCnt >= 3:
            break
    weiboData['weiboId'] = weiboId
    saveJson(weiboData, tempData)

    # 签到
    checkInSucc = False
    while not checkInSucc:
        res = api.checkIn(token)
        print(res['msg'])
        if res['status'] != -1:
            checkInSucc = True
        time.sleep(SLEEPTIME)

    # 增加经验值
    expAfter = getCurrExp(token, userId)
    print('当前经验值：', expAfter, '  增加了：', expAfter-expBefore)


def run(accountFN):
    accounts = loadAccountFromTxt(accountFN)
    print('共有账号%d个'%(len(accounts)))
    cnt = 0
    for accnt in accounts:
        res = api.login(accnt['account'], accnt['password'], type=accnt['type'])
        if res['status'] <= 0:
            print('账号错误：%s，原因：%s\n'%(accnt['account'], res['msg']))
            continue
        print('')
        print('账号：%s'%(accnt['account']))
        levelUp(res['token'], res['userId'])
        cnt += 1
        time.sleep(10)


if __name__ == "__main__":
    api = KD48API()
    # run(accountFN)

    scheduler = BlockingScheduler()
    scheduler.add_job(run, 'cron', args=(accountFN,), hour=9)
    print('每日上午9点，开始自动签到点赞...')
    scheduler.start()
