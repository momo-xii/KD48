# -*- coding:utf-8 -*-
import os
import sys
import time
import math
import logging
import mylog
mylog.setLog('modianMonitor')

from ModianAPI import *
from utility import *
from cqsdk import CQBot, CQAt, RcvdPrivateMessage, RcvdGroupMessage, \
    GroupMemberIncrease, GroupMemberDecrease
import utils
from apscheduler.schedulers.background import BackgroundScheduler

pid = os.getpid()
qqbot = CQBot(11235)

def killmyself():
    killProcess(pid)

def SendDebugMsgs(debugQQ, text):
    utils.error(text)
    if debugQQ:
        utils.SendPrivateMsg(qqbot, str(debugQQ), text.strip())

class MDMonitor(object):
    def __init__(self, params):
        self.debugQQ = params['debugQQ']
        self.QQGroups = params['QQGroups']
        self.wds_id = str(params['wds_id'])
        self.wds_link = params['wds_link']
        self.postMoney = params['postMoney'] - 1e-3

        # 开关
        self.eggEnable = params['eggEnable']
        self.printRankingEnable = params['printRankingEnable']

        # 定时提醒
        self.alertEnable = params['alert']['enable']
        self.alertInterval = params['alert']['interval'] * 60
        self.alertLastTime = time.time()
        self.alertHistory = []

        # 结束倒计时
        self.cdEnable = params['countdown']['enable']
        self.deadline = params['countdown']['deadline']

        # pk
        self.pkEnable = params['pk']['enable']
        self.wds_id_pk = params['pk']['wds_id']
        self.pkFactor = params['pk']['factor']
        if not self.wds_id_pk:
            self.pkEnable = False

        # 状态
        self.wdsIsEnd = False

        # 文件路径
        self.flagtextPath = './config/flag.json'
        self.configPath = './config/modian_config.json'


    def initWDS(self):
        self.wds = WDS()
        self.egg = Egg()

        wdsInfo = self.wds.getProjectDetail(self.wds_id)
        self.end_time = wdsInfo['end_time']
        if self.deadline == "":
            self.deadline = self.end_time
        elif not isVaildTime(self.deadline):
            self.deadline = self.end_time
            utils.warning('配置文件中deadline格式错误，已设置为默认结束时间')

        self.wds.loadStatus()
        if self.wds.wdsLastTime == 0:
            self.wds.getOrders(self.wds_id)

        self.wds.loadFlags()
        self.countMoney = self.wds.flags['baseflag']['level']

        remain = ISOString2Time(self.end_time) - time.time()
        if remain < 0:
            self.wdsIsEnd = True
            print('本次摩点集资已结束')
            os.system('pause')
            killmyself()


    def initial(self):
        try:
            self.initWDS()
        except Exception as e:
            logging.exception(e)
            utils.error('摩点初始化失败！请重新启动。\n', e)


    # 输出集资排行榜
    def postRankingList(self, title='本次摩点排行榜（整点播报）：'):
        rankList = self.wds.getRankingList(self.wds_id, page=1)
        rankList += self.wds.getRankingList(self.wds_id, page=2)
        log = title
        log += '\n选拔组（1-16名）：'
        for i in range(16):
            if i < len(rankList):
                log += '\n%d、%s，总集资额：%.2f元'%(i+1, rankList[i]['nickname'], 
                    float(rankList[i]['backer_money']))
        utils.SendGroupsMsg(qqbot, self.QQGroups, log.strip())
        time.sleep(0.5)
        if len(rankList) >= 32:
            log = title
            log += '\n高飞组（17-32名）：'
            for i in range(16,32):
                if i < len(rankList):
                    log += '\n%d、%s，总集资额：%.2f元'%(i+1, rankList[i]['nickname'], 
                        float(rankList[i]['backer_money']))
            utils.SendGroupsMsg(qqbot, self.QQGroups, log.strip())


    # 计数置零
    def setBaseflagToZero(self):
        self.wds.flags['baseflag']['count'] = 0


    # 载入新的flag
    def loadNewFlag(self):
        try:
            self.wds.loadNewFlag()
        except Exception as e:
            logging.exception(e)
            utils.error('loadNewFlag: ', e)


    # 实时集资监控
    def orderMonitor(self):
        if self.wdsIsEnd:
            return
        # flag text for printing
        flagtxt = loadJson(self.flagtextPath)
        # load eggs
        if self.eggEnable:
            self.egg.load()

        orderList = self.wds.getOrders(self.wds_id)
        if orderList:
            wdsInfo = self.wds.getProjectDetail(self.wds_id)
            if self.pkEnable:
                time.sleep(0.5)
                wdsInfo_pk = self.wds.getProjectDetail(self.wds_id_pk)

            for order in orderList:
                money = float(order['backer_money'])
                self.wds.flagCounters(money)

                # 彩蛋 未检查
                if self.eggEnable:
                    eggExist = False
                    eggs = self.egg.eggs
                    eggMoney = list(eggs.keys())
                    if money in eggMoney:
                        eggExist = True
                        logEgg = '%s 集资了%.2f元，触发了彩蛋【%s】'%(order['nickname'],
                            money, eggs[money]['name'].decode('gb18030'))
                        msg = eggs[money]['msg']
                        if msg != '':
                            logEgg += '\n%s'%(eggs[money]['msg'].decode('gb18030'))
                        if eggExist and money < 34.999:
                            utils.SendGroupsMsg(qqbot, self.QQGroups, logEgg.strip())
                            eggExist = False

                    qpzExist = False
                    if float(wdsInfo['currMoney']) % 100 == 0:
                        qpzExist = True
                        logqpz = '%s 集资了%.2f元，触发了彩蛋【小强迫症】，将集资额凑整百'%(
                            order['nickname'], money)
                    if float(wdsInfo['currMoney']) % 1000 == 0:
                        qpzExist = True
                        logqpz = '%s 集资了%.2f元，触发了彩蛋【中强迫症】，将集资额凑整千'%(
                            order['nickname'], money)
                    if float(wdsInfo['currMoney']) % 10000 == 0:
                        qpzExist = True
                        logqpz = '%s 集资了%.2f元，触发了彩蛋【大强迫症】，将集资额凑整万'%(
                            order['nickname'], money)
                    # if qpzExist and money < 34.999:
                    #     utils.SendGroupsMsg(qqbot, self.QQGroups, logqpz.strip())
                    #     qpzExist = False


                # 前面是所有金额都触发
                if money < self.postMoney:
                    continue

                self.alertLastTime = time.time() #更新警告时间
                self.alertHistory = []

                # 播报
                log = '感谢 %s 在%s中，集资%s元，给爸爸比心(｡･ω･｡)ﾉ♡\n'%(order['nickname'],
                    wdsInfo['topic'], order['backer_money'])
                log += '%d元一棒，今日目前棒数%d棒\n'%(int(self.countMoney),
                    self.wds.flags['baseflag']['count'])
                if self.wds_link:
                    log += '集资链接：%s\n'%(self.wds_link)

                # 统计
                # log += '\n已筹%s元（%s人），目标：%s元'%(wdsInfo['currMoney'],
                #     wdsInfo['num_people'], wdsInfo['targetMoney'])
                log += '已筹：%s元，目标：%s元\n'%(wdsInfo['currMoney'],
                    wdsInfo['targetMoney'])

                if self.cdEnable:
                    cdTime = ISOString2Time(self.deadline) - time.time()#(float(order['ctime']))
                    cdHours = int(cdTime//3600)
                    cdMinutes = int((cdTime%3600)//60)
                    cdSeconds = int(cdTime%60)
                    if cdTime < 0 or cdHours > 24:
                        log += '距本次众筹结束还剩【不到 %d小时】\n'%(cdHours+1)
                        pass
                    elif cdHours > 0:
                        log += '距本次众筹结束还剩【不到 %d小时】\n'%(cdHours+1)
                    elif cdMinutes >= 0:
                        log += '距本次众筹结束还剩【不到 %d分钟】\n'%(cdMinutes+1)
                    # elif cdSeconds > 0:
                    #     log += '距本次众筹结束还剩 %d秒\n'%(cdSeconds)

                # pk播报
                if self.pkEnable:
                    our_money = float(wdsInfo['currMoney'])
                    # our_people = int(wdsInfo['num_people'])
                    pk_money = float(wdsInfo_pk['currMoney'])
                    # pk_people = int(wdsInfo_pk['num_people'])
                    log += '【我方】已筹 %.2f元\n'%(our_money)
                    log += '【对方】已筹 %.2f元\n'%(pk_money)
                    log += '对比系数为 1:%.1f'%(self.pkFactor)
                    if our_money > pk_money*self.pkFactor:
                        log += '目前领先：%.2f元\n'%(our_money - pk_money*self.pkFactor)
                    else:
                        log += '目前落后：%.2f元\n'%(pk_money*self.pkFactor - our_money)

                # 文字flag
                log += flagtxt + '\n'
                utils.SendGroupsMsg(qqbot, self.QQGroups, log.strip())

                if self.eggEnable:
                    if eggExist:
                        utils.SendGroupsMsg(qqbot, self.QQGroups, logEgg.strip())
                    if qpzExist:
                        utils.SendGroupsMsg(qqbot, self.QQGroups, logqpz.strip())

                # flag
                for name in self.wds.flags:
                    if name == 'baseflag':
                        continue
                    flag = self.wds.flags[name]
                    log = 'flag：%s，%.2f元一棒，进度：%d/%d'%(
                        name.decode('gb18030'),flag['level'],flag['count'],flag['target'])
                    if money >= flag['level']:
                        utils.SendGroupsMsg(qqbot, self.QQGroups, log.strip())

                names = list(self.wds.flags.keys())
                for name in names:
                    flag = self.wds.flags[name]
                    if flag['finish'] == 1:
                        log = 'flag【%s】已完成：%.2f元一棒，完成度：%d/%d'%(
                            name.decode('gb18030'),flag['level'],flag['count'],flag['target'])
                        utils.SendGroupsMsg(qqbot, self.QQGroups, log.strip())
                        self.wds.flags.pop(name)
                time.sleep(1)
            self.wds.saveStatus()
            self.wds.saveFlags()


    ##### 定时提醒 #####
    def alertTimer(self):
        if not self.alertEnable:
            return
        if self.wdsIsEnd:
            return
        if time.time() - self.alertLastTime > self.alertInterval:
            minutes = int(math.floor((time.time() - self.alertLastTime) / self.alertInterval)) \
                    * (self.alertInterval/60)
            if (time.time()+28800) % 86400 > 0 and (time.time()+28800) % 86400 < 3600*9:
                pass
            elif minutes not in self.alertHistory:
                log = '过去%d分钟内无人接棒'%minutes
                utils.SendGroupsMsg(qqbot, self.QQGroups, log.strip())
                self.alertHistory.append(minutes)

    # 检测此集资链接是否结束
    def endingMonitor(self):
        remain = ISOString2Time(self.end_time) - time.time()
        if remain < 0:
            self.wdsIsEnd = True
            # 输出微打赏信息
            wdsInfo = self.wds.getProjectDetail(self.wds_id)
            log = '本次摩点众筹已结束，感谢大家支持！\n'
            log += '\n本次摩点共筹：%s元\n'%(wdsInfo['currMoney'])
            # log += '\n\n本次微打赏共筹：%s元，参与人数：%s人'%(wdsInfo['currMoney'],
            #     wdsInfo['num_people'])
            utils.SendGroupsMsg(qqbot, self.QQGroups, log.strip())
            time.sleep(0.5)
            # 输出排行榜
            self.postRankingList(title='本次摩点众筹最终排行榜：')

            print('本次摩点众筹已结束，按任意键退出监控程序。')
            os.system('pause')
            killmyself()


    def run(self):
        print('正在启动摩点众筹监控...')

        self.scheduler = BackgroundScheduler()

        self.scheduler.add_job(self.orderMonitor, 'interval', seconds=10, id='orderMonitor',
            coalesce=True, max_instances=1)

        self.scheduler.add_job(self.alertTimer, 'interval', seconds=10, id='alertTimer',
            coalesce=True, max_instances=1)

        self.scheduler.add_job(self.endingMonitor, 'interval', seconds=10, id='endingMonitor',
            coalesce=True, max_instances=1)
        
        self.scheduler.add_job(self.loadNewFlag, 'interval', seconds=10, id='loadNewFlag',
            coalesce=True, max_instances=1)

        self.scheduler.add_job(self.setBaseflagToZero, 'cron', hour=0, id='tozero', 
            misfire_grace_time=300, coalesce=True)

        if wdsParams['printRankingEnable']:
            # 每日9-24点整点播报排行榜
            self.scheduler.add_job(self.postRankingList, 'cron', hour='9-23,0', id='postrank', 
                misfire_grace_time=60, coalesce=True)

        self.scheduler.start()

        print('所有监控器启动完毕')



############ 自动回复消息设置 #############
from config import modian_admins
group_admins = modian_admins.admins['Group']
private_admins = modian_admins.admins['Private']

# level: 0-forbid, 1-admin, 2-all
groupCmdAuthority = {#"排行榜": {'level': 1, 'lastTime': {}}, 
           }

def ReplyHandler(msg):
    result = ''
    msgs = msg.split()
    try:
        if msgs[0] == '更新flag':
            txt = msg.lstrip('更新flag').strip()
            saveJson(txt, self.flagtextPath)
            result = '成功更新flag内容，回复【查看flag】查看最新flag'

        if msgs[0] == '查看flag':
            result = loadJson(self.flagtextPath)

    except Exception as e:
        logging.exception(e)
    finally:
        return result


# 处理群消息
@qqbot.listener((RcvdGroupMessage,))
def ReplyGroupMsg(message):
    if message.text.strip() == "":
        return
    global groupCmdAuthority
    global group_admins
    currQQLevel = 100
    result = ''
    if message.group in group_admins:
        if message.qq in group_admins[message.group]:
            currQQLevel = 1
        else:
            currQQLevel = 2
        if 'all' in group_admins[message.group]:
            currQQLevel = 1
    if message.text in groupCmdAuthority:
        level = groupCmdAuthority[message.text]['level']
        lastTimeDict = groupCmdAuthority[message.text]['lastTime']
        if message.group not in lastTimeDict:
            lastTimeDict[message.group] = 0
            lastTime = 0
        else:
            lastTime = lastTimeDict[message.group]
        # 命令冷却时间300秒
        if currQQLevel <= level and time.time() - lastTime >= 300:
            result = ReplyHandler(message.text)
            lastTimeDict[message.group] = time.time()

    if result:
        msg = "{text}\n{qq}".format(text=result, qq=CQAt(message.qq))
        utils.reply(qqbot, message, msg)


# 处理私聊消息
@qqbot.listener((RcvdPrivateMessage,))
def ReplyRrivateMsg(message):
    if message.text.strip() == "":
        return
    global private_admins
    result = ''
    if message.qq in private_admins:
        result = ReplyHandler(message.text)

    if result:
        utils.reply(qqbot, message, result)



############### 启动监控程序 #################
try:
    qqbot.start()
    wdsParams = loadJson('./config/modian_config.json')
    monitor = MDMonitor(params=wdsParams)
    monitor.initial()
    monitor.run()
except Exception as e:
    logging.exception(e)
    utils.error('启动失败\n', e)
    os.system('pause')
    sys.exit()

# 主程序循环，防止退出程序
while True:
    time.sleep(100)
