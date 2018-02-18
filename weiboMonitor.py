# -*- coding:utf-8 -*-
import os
import sys
import time
from datetime import datetime
import math
import threading
import random
import urllib.request as request
import logging
import mylog
mylog.setLog('weiboMonitor', logging.WARNING)

from utility import *
from cqsdk import CQBot, CQAt, RcvdPrivateMessage, RcvdGroupMessage, \
    GroupMemberIncrease, GroupMemberDecrease
import utils
from weiboAPI import Weibo
from apscheduler.schedulers.background import BackgroundScheduler

pid = os.getpid()
qqbot = CQBot(11235)

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


############ 自动回复消息设置 #############
from config import weibo_admins
group_admins = weibo_admins.admins['Group']
private_admins = weibo_admins.admins['Private']
QQGroups = weibo_admins.QQGroups
adminQQ = weibo_admins.adminQQ
QQGroups_lite = weibo_admins.QQGroups_lite
memberName = weibo_admins.memberName

# 每个group分别有个lasttime
# 'lastTime': {'group1':0, 'group2':0}
# level: 0:全体禁止 1:管理员命令 2:普通成员命令
groupCmdAuthority = {"超话数据": {'level': 1, 'lastTime': {}},
                     "微博故事": {'level': 1, 'lastTime': {}},
                     "添加微博故事监控": {'level': 1, 'lastTime': {}},
                     "移除微博故事监控": {'level': 1, 'lastTime': {}},
                    }

def ReplyHandler(msg):
    global groupCmdAuthority
    result = ''
    try:
        if msg == "命令列表":
            result += '微博命令列表：\n'
            for comm in sorted(groupCmdAuthority):
                result += comm + '\n'
            result = result.strip()

        if msg == "超话数据":
            result = getSuperTopicInfo()

        if msg.split()[0] == "微博故事":
            weibo_id = ''
            if len(msg.split()) == 1:
                weibo_id = ''
            elif len(msg.split()) ==2:
                weibo_id = msg.split()[1]
            else:
                return '参数错误'
            result = printStoryInfo(weibo_id)

        if msg == "添加微博故事监控":
            scheduler.add_job(checkStory, 'interval', seconds=5, id='story', 
                misfire_grace_time=5, coalesce=True)
            result = '添加成功'

        if msg == "移除微博故事监控":
            scheduler.remove_job('story')
            result = 'checkStory: job story removed.'
        
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
   
    if result:
        utils.reply(qqbot, message, result)


qqbot.start()

##### 微博信息监控 #####
weibo = Weibo()
storyLastTime = 0
# 初始化微博故事
res = weibo.getStory2()
if res['status'] > 0:
    storyLastTime = res['data'][-1]['create_time']
elif res['status'] == 0:
    pass
else:
    log = res['msg']
    SendDebugMsgs(adminQQ[0], log)
    sys.exit()

PrintLog('初始化微博故事成功')

def checkStory():
    global storyLastTime
    result = weibo.getStory2()
    story = result['data']
    if result['status'] > 0:
        for s in story:
            if storyLastTime < s['create_time']:
                # 抢沙发
                try:
                    comment = '沙发'
                    segment_id = s['segment_id']
                    story_id = s['story_id']
                    r = weibo.postStoryComment(comment, segment_id, story_id)
                    if r['status'] < 0:
                        print('评论失败：%s'%r['msg'])
                except Exception as e:
                    pass
                # 播报
                log = '%s 发布微博故事了！大家快去微博评论点赞啦！\n'%(s['nickname'])
                utils.SendGroupsMsg(qqbot, QQGroups_lite, log.strip())
                storyLastTime = s['create_time']
                log += "视频地址：" + s['url'] + "\n"
                log += "视频时长：%.1fs"%(s['duration']/1000)
                utils.SendGroupsMsg(qqbot, QQGroups, log.strip())
                utils.SendPrivatesMsg(qqbot, adminQQ, log)
                # 下载微博故事
                try:
                    storyDir = './download/story/'
                    mkdir(storyDir)
                    fn = getISODateAndTime().replace(':','') + '.mp4'
                    request.urlretrieve(s['url'], filename=os.path.join(storyDir, fn))
                except Exception as e:
                    text = '下载失败！'
                    logging.error(text)
                    logging.exception(e)

    elif result['status'] == -2:
        errorsList = ['未知错误', '校验参数不存在', '系统繁忙', 'invalid weibo user!', 
        "API config 'api.main.stories_details' is wrong or invalid!", 'short circuit']
        logging.warning('checkStory: ' + result['msg'])
        if result['msg'] in errorsList:
            return
        utils.SendPrivatesMsg(qqbot, adminQQ, 'checkStory: ' + result['msg'])
        # scheduler.remove_job('story')
        # utils.SendPrivatesMsg(qqbot, adminQQ, 'checkStory: job story removed.')


def printStoryInfo(weibo_id=''):
    result = ''
    if weibo_id:
        if weibo_id.isdigit():
            res = weibo.getStory2(weibo_id)
        else:
            weiboIdDict = loadJson('config/weiboid.json')
            if weibo_id in weiboIdDict:
                res = weibo.getStory2(weiboIdDict[weibo_id])
            else:
                return '参数无效'
    else:
        res = weibo.getStory2()
    story = res['data']
    nickname = res['nickname']
    if res['status'] > 0:
        result = '%s 发布的微博故事：\n'%(nickname)
        for s in story:
            result += "视频地址：" + s['url'] + "\n"
            result += "视频时长：%.1fs"%(s['duration']/1000) + "\n"
            result += "评论数量：" + str(s['comment_count']) + "\n"
            result += "播放数量：" + str(s['play_count']) + "\n"
            result += "点赞数量：" + str(s['like_count']) + "\n"
            result += "分享数量：" + str(s['share_count']) + "\n"
            if s['rank_text']:
                result += "热门排行：" + str(s['rank_text']) + "\n"
            result += "发布时间：" + str(Time2ISOString(s['create_time'])) + "\n"
            # result += "story_id：" + str(s['story_id']) + "\n"
            # result += "segment_id：" + str(s['segment_id']) + "\n"
            result += "\n"
    elif res['status'] == -2:
        result = res['msg']
    else:
        result = '%s 没有发布微博故事'%(nickname)
    return result.strip()


# 初始化topic信息
topiclogFN = 'config/superTopic.json'
topicInfoOld = None
if not os.path.exists(topiclogFN):
    topicInfo = weibo.getChaohuaStat()
    while not topicInfo:
        time.sleep(3)
        topicInfo = weibo.getChaohuaStat()
    saveJson(topicInfo, topiclogFN)
    topicInfoOld = topicInfo
else:
    topicInfoOld = loadJson(topiclogFN)

def checkSuperTopic():
    global topicInfoOld
    topicInfo = weibo.getChaohuaStat()
    visitCnt = 0
    while not topicInfo:
        if visitCnt >= 10:
            return
        visitCnt += 1
        time.sleep(3)
        topicInfo = weibo.getChaohuaStat()
    log = '#%s# 超话数据：\n'%(memberName)
    log += '时间：%s'%topicInfo['date'] + '\n'
    log += '粉丝：%s，增加了：%d'%(topicInfo['fansCnt'], 
        topicInfo['fansCnt'] - topicInfoOld['fansCnt']) + '\n'
    log += '帖子：%s，增加了：%d'%(topicInfo['postCnt'], 
        topicInfo['postCnt'] - topicInfoOld['postCnt'])
    utils.SendPrivatesMsg(qqbot, adminQQ, log)
    topicInfoOld = topicInfo
    saveJson(topicInfoOld, topiclogFN)

def getSuperTopicInfo():
    topicInfo = weibo.getChaohuaStat()
    if topicInfo:
        log = '#%s# 超话数据：\n'%(memberName)
        log += '时间：%s'%topicInfo['date'] + '\n'
        log += '阅读：%.2f亿'%(topicInfo['viewCnt']/1e8) + '\n'
        log += '帖子：%s'%topicInfo['postCnt'] + '\n'
        log += '粉丝：%s'%topicInfo['fansCnt'] + '\n'
        return log.strip()
    else:
        return "发生错误"

def weiboCheckIn():
    data = weibo.checkIn()
    while data['status'] == -1:
        time.sleep(3)
        data = weibo.checkIn()
    if data['status'] == 1:
        topicInfoOld['checkCnt'] = data['check_count']
        topicInfoOld['checkInState'] = 1
        saveJson(topicInfoOld, topiclogFN)
    else:
        topicInfoOld['checkInState'] = 0
        utils.SendPrivatesMsg(qqbot, adminQQ, '发生错误，可能已签到')

def sendWeiboCheckIn():
    if topicInfoOld['checkInState'] == 1:
        log = '#%s# 超话昨日签到人数：%d人'%(memberName, 
            topicInfoOld['checkCnt'])
    else:
        log = '签到发生错误'
    utils.SendPrivatesMsg(qqbot, adminQQ, log)


scheduler = BackgroundScheduler()

scheduler.add_job(checkStory, 'interval', seconds=5, id='story', 
    misfire_grace_time=5, coalesce=True)

scheduler.add_job(checkSuperTopic, 'cron', hour=22, id='topic', 
    misfire_grace_time=60, coalesce=True)

scheduler.add_job(weiboCheckIn, 'cron', hour=23, minute=59, id='checkIn', 
    misfire_grace_time=60, coalesce=True)

scheduler.add_job(sendWeiboCheckIn, 'cron', hour=0, minute=5, id='sendCheckIn', 
    misfire_grace_time=60, coalesce=True)

scheduler.start()
PrintLog("开始监控微博故事和超话数据...")
PrintLog("所有监控器启动完毕")

# 主程序循环，防止退出程序
while True:
    time.sleep(100)
