# -*- coding:utf-8 -*-
import os
import sys
import time
import math
import threading
import random
import logging
import mylog
mylog.setLog('KD48Monitor', logging.WARNING)

loggerInfo = logging.getLogger('mylogger')
loggerInfo.setLevel(logging.INFO)
fh = logging.FileHandler('./log/info.log')
formatter = logging.Formatter('%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s')
fh.setFormatter(formatter)
loggerInfo.addHandler(fh)

from utility import *
from KD48API import KD48API
from longQQMsg import LongQQMsg
from MsgCounter import MsgCounter

from cqsdk import CQBot, CQAt, RcvdPrivateMessage, RcvdGroupMessage, \
    GroupMemberIncrease, GroupMemberDecrease
import utils
from weiboAPI import Weibo
from apscheduler.schedulers.background import BackgroundScheduler

pid = os.getpid()
qqbot = CQBot(11235)
longQQMsg = LongQQMsg()

def killmyself():
    killProcess(pid)

def SendDebugMsgs(debugQQ, t):
    PrintLog(t)
    if debugQQ:
        utils.SendPrivateMsg(qqbot, str(debugQQ), t)

def PrintLog(text):
    currTimeStr = Time2ISOString(time.time())
    print(currTimeStr, text)
    logging.info('PrintLog ' + text)
    loggerInfo.info('PrintLog ' + text)

class KD48Monitor(object):
    def __init__(self, accountInfo, monitorInfo):
        # 登录信息
        self.account = accountInfo['userId']
        self.password = accountInfo['password']
        self.token = '0'

        # debugQQ: 接收错误信息
        self.debugQQ = accountInfo['debugQQ']

        # 接收消息QQ设置
        # QQGroups_pro: 转发所有消息
        # QQGroups_lite: 只提示房间出现，不转发消息（TODO：自己可以设置转发哪些内容）
        # QQIds: 私聊转发所有消息
        self.QQIds = monitorInfo['QQIds']
        self.QQGroups_pro = monitorInfo['QQGroups_pro']
        if 'QQGroups_lite' in list(monitorInfo.keys()):
            self.QQGroups_lite = monitorInfo['QQGroups_lite']
        else:
            self.QQGroups_lite = []
        self.QQGroups_all = list(set(self.QQGroups_pro).union(set(self.QQGroups_lite)))

        # 被监控成员的信息
        self.memberId = monitorInfo['memberId']
        self.memberName = ''
        self.roomId = None
        self.groupId = 0
        self.roomInfo = {}
        self.roomInfoOld = {}
        self.beginHot = 0

        # CoolQ
        self.CoolQRoot = monitorInfo['CoolQRoot']
        # self.CoolQImageDir = os.path.join(self.CoolQRoot, 'data', 'image')

        # room msg alert
        self.isappeared = False
        self.timegap = 1800 #second
        self.lastPrintTime = time.time()
        self.msgCounter = MsgCounter()
        self.lastOtherMemberTime = 0 #上次在房间出现其他成员的时间


    # 更新房间信息
    def updateRoomInfo(self):
        response = self.api.getRoomInfo(self.token, self.memberId)
        if response['status'] != -1:
            self.roomInfo = response['data']
            return 1
        else:
            return -1

    # 打印房间信息
    def printRoomInfo(self):
        self.updateRoomInfo()
        currHot = self.getRoomHot()
        info = ''
        if self.roomInfo:
            info += self.roomInfo['memberName'] + '的房间：' + '\n'
            info += '房间名称：' + filter_emoji(self.roomInfo['roomName']) + '\n'
            info += '房间话题：' + filter_emoji(self.roomInfo['topic']) + '\n'
            info += '房间心情：' + filter_emoji(self.roomInfo['moodName']) + '\n'
            info += '房间热度：' + str(currHot) + '\n'
            # info += '最后发言时间：' + self.roomInfo['lastCommentTime'] + '\n'
            info += '房间头像：' + self.roomInfo['roomAvatar'] + '\n'
            info += '房间背景：' + self.roomInfo['bgPath']
        else:
            info += '当前房间为空'
        return info


    def checkRoom(self):
        self.updateRoomInfo()
        monitorDicts = {'roomName'  :  '房间名称',
                        'topic'     :  '房间话题',
                        'moodName'  :  '房间心情',
                        'roomAvatar':  '房间头像',
                        'bgPath'    :  '房间背景'
                        }
        modifiedKeys = []
        response = ''
        for key in list(monitorDicts.keys()):
            if self.roomInfo[key] != self.roomInfoOld[key]:
                modifiedKeys.append(key)
        if modifiedKeys:
            response = self.memberName + '修改了房间信息'
            for key in modifiedKeys:
                response += '\n修改了' + monitorDicts[key] + '：' + self.roomInfo[key]
            self.roomInfoOld = self.roomInfo
            saveJson(self.roomInfoOld, 'config/roomInfo.json')
        return response


    def getRoomHot(self):
        '''获取当前成员的房间热度
        '''
        page = 1
        while True:
            result = self.api.getHotRooms(self.token, page=page, 
                groupId=self.groupId)
            hotRooms = result['data']
            if self.memberId in hotRooms:
                return hotRooms[self.memberId]['hot']
            else:
                page += 1
            if not hotRooms:
                return -1


    def initKD(self):
        self.api = KD48API()

        # 登录获取token
        interval = 10
        loginSucc = False
        loginCnt = 0
        while not loginSucc:
            response = self.api.login(self.account, self.password)
            if response['status'] != -1:
                self.token = response['token']
                loginSucc = True
                log = response['msg']
                PrintLog(log)
            else:
                loginCnt += 1
                log = response['msg']
                PrintLog(log)
                PrintLog('%d秒钟后重试...'%interval)
                time.sleep(interval)
            if loginCnt >= 10:
                PrintLog('登录失败！请重新启动。')
                os.system('pause')
                sys.exit()

        # 根据成员ID获取房间其他信息
        interval = 10
        rinfoSucc = False
        rinfoCnt = 0
        while not rinfoSucc:
            response = self.api.getRoomInfo(self.token, self.memberId)
            if response['status'] != -1:
                self.roomInfo = response['data']
                self.roomId = response['data']['roomId']
                self.memberName = response['data']['memberName']
                self.groupId = response['data']['groupId']
                rinfoSucc = True
                log = response['msg']
                PrintLog(log)
            else:
                rinfoCnt += 1
                log = response['msg']
                PrintLog(log)
                PrintLog('%d秒钟后重试...'%interval)
                time.sleep(interval)
            if rinfoCnt >= 10:
                PrintLog('获取房间信息失败！请重新启动。')
                os.system('pause')
                sys.exit()

        # 初始化
        self.msgLastTime = 0
        self.oldLiveIds = []
        self.oldReviewIds = []

        response = self.api.getRoomMsgs(self.token, self.roomId)
        if response['status'] != -1:
            messages = response['data']
            self.msgLastTime = messages[0]['msgTime']
            PrintLog('初始化房间成功')
        else:
            log = response['msg']
            PrintLog(log)
            os.system('pause')
            sys.exit()

        response = self.api.getLiveList(self.token, memberId=self.memberId, limit=30)
        if response['status'] != -1:
            liveList = response['liveList']
            reviewList = response['reviewList']
            if liveList:
                for live in reversed(liveList):
                    self.oldLiveIds.append(live['liveId'])
            if reviewList:
                for review in reversed(reviewList):
                    self.oldReviewIds.append(review['liveId'])
            PrintLog('初始化直播成功')
        else:
            log = response['msg']
            PrintLog(log)
            os.system('pause')
            sys.exit()

        self.roomInfoPath = 'config/roomInfo.json'
        if not os.path.exists(self.roomInfoPath):
            saveJson(self.roomInfo, self.roomInfoPath)
            self.roomInfoOld = self.roomInfo
        else:
            self.roomInfoOld = loadJson(self.roomInfoPath)


    def initial(self):
        try:
            self.initKD()
        except Exception as e:
            logging.exception(e)
            PrintLog('口袋监控初始化失败！请重新启动程序。')
            os.system('pause')
            sys.exit()


    def roomMonitor(self):
        try:
            messages = []
            response = self.api.getRoomMsgs(self.token, self.roomId)
            if response['status'] != -1:
                messages = response['data']

            for msg in reversed(messages):
                if msg['msgTime'] <= self.msgLastTime:
                    continue
                msgInfo = self.api.analyzeMsg(msg, self.CoolQRoot)
                if msgInfo['ignore']:
                    continue
                # 其他成员发消息
                if msgInfo['senderId'] != self.memberId and msgInfo['senderId'] > 0:
                    # 半小时内只播报一次 TODO: 对不同成员分别计时
                    if time.time()-self.lastOtherMemberTime > 1800: 
                        self.lastOtherMemberTime = time.time()
                        # log = '%s在%s口袋房间出现了！'%(
                        #     msgInfo['senderName'], self.memberName)
                        log = '其他成员在%s口袋房间出现了！快去看看是谁！'%(self.memberName)
                        utils.SendPrivatesMsg(qqbot, self.QQIds, log.strip())
                        utils.SendGroupsMsg(qqbot, self.QQGroups_all, log.strip())
                    log = msgInfo['printText'].strip() + '\n来自%s口袋房间'%(self.memberName)
                    utils.SendPrivatesMsg(qqbot, self.QQIds, log.strip())
                    utils.SendGroupsMsg(qqbot, self.QQGroups_pro, log.strip())
                    # self.msgLastTime = msgInfo['msgTime']
                else:  # 房间拥有者发消息
                    # 通知判定，半小时为临界点
                    # 改进TODO：计算当前消息和上一条消息的时间差来判定，不再记录时间
                    #           但上一条消息要确保是本房间拥有者发的消息，不能是其他成员
                    if self.isappeared == False:
                        self.isappeared = True
                        log = (self.memberName + '在口袋房间出现了！大家快去调戏互动啦！' 
                            '（具体消息暂停搬运，请大家移步口袋房间）')
                        utils.SendPrivatesMsg(qqbot, self.QQIds, log)
                        utils.SendGroupsMsg(qqbot, self.QQGroups_all, log)
                        self.beginHot = self.getRoomHot()
                        time.sleep(1)
                    elif time.time() - self.msgLastTime / 1000.0 > 600:
                        log = self.memberName + '又在房间出现啦！'
                        utils.SendPrivatesMsg(qqbot, self.QQIds, log)
                        # utils.SendGroupsMsg(qqbot, self.QQGroups_all, log)
                        self.msgLastTime = msgInfo['msgTime']
                        time.sleep(1)
                    # 转发消息
                    log = msgInfo['printText']
                    utils.SendPrivatesMsg(qqbot, self.QQIds, log.strip())
                    utils.SendGroupsMsg(qqbot, self.QQGroups_pro, log.strip())
                    if msgInfo['messageObject'] == 'faipaiText':
                        utils.SendGroupsMsg(qqbot, self.QQGroups_lite, log.strip())
                    self.msgCounter.counter(msgInfo)
                    self.lastPrintTime = time.time()
                    # 下载非文字消息
                    try:
                        download_thread = threading.Thread(
                            target=self.api.downloadMsg, args=(msgInfo,), daemon=True)
                        download_thread.start()
                    except Exception as e:
                        SendDebugMsgs(self.debugQQ, '多线程下载错误！')
                        logging.exception(e)
                    time.sleep(1)
            if messages:
                self.msgLastTime = messages[0]['msgTime'] # msgInfo['msgTime']
                    
            # 消息统计
            if time.time() - self.lastPrintTime > self.timegap and self.isappeared == True:
                self.isappeared = False
                log = self.memberName + '从房间消失了半个小时了......\n'
                log += self.msgCounter.info()
                self.msgCounter.reset()
                deltaHot = self.getRoomHot() - self.beginHot
                log += "\n房间热度增加了：%d"%deltaHot
                utils.SendPrivatesMsg(qqbot, self.QQIds, log.strip())
                utils.SendGroupsMsg(qqbot, self.QQGroups_all, log.strip())
        except Exception as e:
            SendDebugMsgs(self.debugQQ, '房间消息解析错误！')
            logging.exception(e)
            # 如果出错，则跳过这几条消息
            self.msgLastTime = messages[0]['msgTime']


    def liveMonitor(self):
        try:
            liveList = []
            reviewList = []
            response = self.api.getLiveList(self.token, memberId=self.memberId)
            if response['status'] != -1:
                liveList = response['liveList']
                reviewList = response['reviewList']

            for live in reversed(liveList):
                if live['liveId'] not in self.oldLiveIds:
                    self.oldLiveIds.append(live['liveId'])
                    if live['memberId'] == self.memberId:
                        liveInfo = self.api.getLiveInfo(live, isLive=True)
                        log = live['title'] + "开始直播了！\n"
                        log += liveInfo['printText']
                        utils.SendPrivatesMsg(qqbot, self.QQIds, log.strip())
                        utils.SendGroupsMsg(qqbot, self.QQGroups_all, log.strip())
                        
                        secret = "直播封面图：" + liveInfo['picPath'] + "\n"
                        secret += "弹幕文件：" + liveInfo['lrcPath'] + "\n"
                        secret += "直播源：" + liveInfo['streamPath']
                        SendDebugMsgs(self.debugQQ, secret.strip())
            if not liveList and response['status'] != -1:
                del self.oldLiveIds[:]

            for review in reversed(reviewList):
                if review['liveId'] not in self.oldReviewIds:
                    if review['liveId'] in self.oldLiveIds:
                        self.oldLiveIds.remove(review['liveId'])
                    self.oldReviewIds.append(review['liveId'])
                    # self.oldReviewIds.pop(0)
                    if review['memberId'] == self.memberId:
                        liveInfo = self.api.getLiveInfo(review, isLive=False)
                        log = review['title'] + "的最新直播回放已出！\n"
                        log += liveInfo['printText']
                        utils.SendPrivatesMsg(qqbot, self.QQIds, log.strip())
                        utils.SendGroupsMsg(qqbot, self.QQGroups_all, log.strip())
        except Exception as e:
            SendDebugMsgs(self.debugQQ, '直播消息解析错误！')
            logging.exception(e)


    def run(self):
        PrintLog('正在启动口袋监控...')

        self.scheduler = BackgroundScheduler()

        self.scheduler.add_job(self.roomMonitor, 'interval', seconds=15, id='roomMonitor',
            coalesce=True, max_instances=1)

        time.sleep(5)

        self.scheduler.add_job(self.liveMonitor, 'interval', seconds=15, id='liveMonitor',
            coalesce=True, max_instances=1)

        time.sleep(3)

        self.scheduler.add_job(self.checkRoom, 'interval', seconds=30, id='checkroom',
            coalesce=True, max_instances=1)

        self.scheduler.start()

        PrintLog('所有监控器启动完毕')


##### 群管理设置 #####
from config import KD_admins
group_admins = KD_admins.admins['Group']
private_admins = KD_admins.admins['Private']
QQGroups = KD_admins.QQGroups
QQGroups_lite = KD_admins.QQGroups_lite
adminQQ = KD_admins.adminQQ
welcomeGroups = KD_admins.welcomeGroups

# 每个group分别有个lasttime
# 'lastTime': {'group1':0, 'group2':0}
# level: 0:全体禁止 1:管理员命令 2:普通成员命令
groupCmdAuthority = {"房间信息": {'level': 1, 'lastTime': {}},
                     "直播回放": {'level': 1, 'lastTime': {}},
                     "集资链接": {'level': 2, 'lastTime': {}},
                     "补档列表": {'level': 1, 'lastTime': {}},
                     "房间消息回放": {'level': 1, 'lastTime': {}},
                    }


############ 自动回复消息设置 #############
def ReplyHandler(msg):
    global groupCmdAuthority
    result = ''
    try:
        if msg == "命令列表":
            result += '口袋命令列表：\n'
            for comm in sorted(groupCmdAuthority):
                result += comm + '\n'
            result = result.strip()

        if msg == "房间信息":
            result = monitor.printRoomInfo()

        if msg == "直播回放":
            response = monitor.api.getLiveList(monitor.token, memberId=monitor.memberId)
            if response['status'] != -1:
                reviewList = response['reviewList']
                review = reviewList[0]
                reviewInfo = monitor.api.getLiveInfo(review, isLive=False)
                result = monitor.memberName + "最近的一次直播是：\n"
                result += reviewInfo['printText']
            else:
                result = '发生错误，请重试！'

        if msg.split()[0] == "房间消息回放":
            limit = 1
            if len(msg.split()) == 1:
                limit = 1
            elif len(msg.split()) == 2:
                limit = int(msg.split()[1])
            else:
                return '参数错误'
            response = monitor.api.getRoomMsgs(monitor.token, monitor.roomId, limit=limit)
            if response['status'] != -1:
                messages = response['data']
                result = monitor.memberName + "房间消息回放：\n"
                for msg in reversed(messages):
                    msgInfo = monitor.api.analyzeMsg(msg)
                    result += msgInfo['printText'] + '\n\n'
            else:
                result = '发生错误，请重试！'

        if "淘宝链接" in msg or "集资链接" in msg:
            result = longQQMsg.taobao

        if msg == "补档列表":
            result = longQQMsg.videoList

    except Exception as e:
        logging.exception(e)
    finally:
        return result.strip()


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
    currCommand = message.text.split()[0]
    if currCommand in groupCmdAuthority:
        level = groupCmdAuthority[currCommand]['level']
        lastTimeDict = groupCmdAuthority[currCommand]['lastTime']
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
        # 强制关闭
        if message.text == '强制关闭口袋监控':
            utils.reply(qqbot, message, '你确定要强制关闭吗？\n'
                '若确定，请回复“我确定强制关闭口袋监控”')
        if message.text == '我确定强制关闭口袋监控':
            try:
                killmyself()
                utils.reply(qqbot, message, '关闭成功')
            except Exception as e:
                utils.reply(qqbot, message, '关闭失败')
    if result:
        utils.reply(qqbot, message, result)


##### 新人加群 #####
@qqbot.listener((GroupMemberIncrease))
def Welcome(message):
    # QQ群自动欢迎，并私聊安利信息
    if message.group in welcomeGroups:
        try:
            text = longQQMsg.welcome
            wel = "欢迎新成员 {qq} \n{text}".format(qq=CQAt(message.operatedQQ), text=text)
            time.sleep(0.5)
            utils.SendGroupMsg(qqbot, message.group, wel)

            time.sleep(3)
            textPrivate = "{qq} {msg}".format(qq=CQAt(message.operatedQQ), 
                msg=longQQMsg.newMemberPrivateMsg)
            utils.SendPrivateMsg(qqbot, message.operatedQQ, textPrivate)
        except Exception as e:
            logging.exception(e)
            PrintLog(e)
    else: #其他群
        pass
    PrintLog('有新人加群 Group: %s Join QQ: %s Admin QQ: %s'%(message.group, 
        message.operatedQQ, message.qq))


##### 退群监控 #####
@qqbot.listener((GroupMemberDecrease))
def GroupMemberQuit(message):
    log = '有人已退群 Group: %s Quit QQ: %s Admin QQ: %s'%(message.group, 
        message.operatedQQ, message.qq)
    PrintLog(log)


##### 口袋房间监控 #####
try:
    qqbot.start()
    [accountInfo, monitorInfo] = loadJson('./config/monitor.json')
    monitor = KD48Monitor(accountInfo, monitorInfo)
    monitor.initial()
    monitor.run()
except Exception as e:
    logging.exception(e)
    utils.error('启动失败\n')
    PrintLog(e)
    os.system('pause')
    sys.exit()

# 主程序循环，防止退出程序
while True:
    time.sleep(100)
