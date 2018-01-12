# -*- coding:utf-8 -*-
import os
import time
from datetime import datetime, timedelta
from utility import *

from cqsdk import CQBot, CQAt, RcvdPrivateMessage, RcvdGroupMessage
import utils

import apscheduler.events as events
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

qqbot = CQBot(11235)


def SendPrivateMsgs(QQIds, t):
    if QQIds:
        for i in QQIds:
            utils.SendPrivateMsg(qqbot, str(i), t.strip())

def SendGroupMsgs(QQgroupIds, t):
    if QQgroupIds:
        for g in QQgroupIds:
            utils.SendGroupMsg(qqbot, str(g), t.strip())

def getNameAndPS(nameAndPS):
    name = nameAndPS.split()[0]
    ps = nameAndPS.lstrip(name).strip()
    return [name, ps]

# 获取当日行程
def getTodayJob():
    text = ''
    todayHasJob = False
    listAllJobs()
    for job in jobList:
        if datetime.date(job['datetime']) == datetime.date(datetime.now()):
            text += '\n' + job['name']
            text += '\n' + '时间：' + job['time']
            todayHasJob = True
    if not todayHasJob:
        text += '无'
    return text

# 每天行程播报
def morningHello():
    text = "各位%s早上好，今天是%d年%d月%d日\n"%(fansName, datetime.now().year, 
        datetime.now().month, datetime.now().day)
    text += "%s今日行程："%(memberName)
    text += getTodayJob()
    SendGroupMsgs(QQGroups, text)
    SendPrivateMsgs(QQIds, text)

# 日常任务
def dailyAlert():
    global dailyJson
    text = ''
    if dailyJson['task']:
        text = dailyJson['task']
    SendGroupMsgs(QQGroups_daily, text)

# 行程提醒
def jobAlert(name, time):
    [jobName, ps] = getNameAndPS(name)
    text = '【%s行程提醒】即将开始：\n'%(memberName)
    text += jobName + '\n'
    text += '时间：' + str(time) + '\n'
    text += '\n' + ps
    text = text.strip()
    if ':' in time:
        SendGroupMsgs(QQGroups, text)
        SendPrivateMsgs(QQIds, text)

def my_listener(event):
    currTimeStr = Time2ISOString(time.time())
    if event.code == events.EVENT_JOB_ADDED:
        print(currTimeStr, 'Job added.')
    elif event.code == events.EVENT_JOB_REMOVED:
        print(currTimeStr, 'Job removed.')
    elif event.code == events.EVENT_JOB_MODIFIED:
        print(currTimeStr, 'Job modified.')
    elif event.code == events.EVENT_JOB_SUBMITTED:
        print(currTimeStr, 'Job submitted.')
    elif event.code == events.EVENT_JOB_MAX_INSTANCES:
        print(currTimeStr, 'Job reached max instances.')
    elif event.code == events.EVENT_JOB_EXECUTED:
        print(currTimeStr, 'Job executed.')
    elif event.code == events.EVENT_JOB_ERROR:
        print(currTimeStr, 'Job error.')
    elif event.code == events.EVENT_JOB_MISSED:
        print(currTimeStr, 'Job missed.')
    elif event.code == events.EVENT_ALL_JOBS_REMOVED:
        print(currTimeStr, 'All jobs removed.')
    elif event.code == events.EVENT_JOBSTORE_ADDED:
        print(currTimeStr, 'Jobstore added.')
    elif event.code == events.EVENT_JOBSTORE_REMOVED:
        print(currTimeStr, 'Jobstore removed.')


jobList = []
def listAllJobs():
    jobList.clear()
    jobs = scheduler.get_jobs(jobstore='default')
    for job in jobs:
        jobInfo = {}
        jobInfo['id'] = job.id
        if job.name[0] == '*':
            jobInfo['name'] = job.name[1:]
            jobInfo['time'] = str(job.next_run_time).split(' ')[0]
            jobInfo['datetime'] = job.next_run_time
        else:
            jobInfo['name'] = getNameAndPS(job.name)[0]
            jobInfo['time'] = str(job.next_run_time + alertDelta).split('+')[0]
            jobInfo['datetime'] = job.next_run_time
            jobInfo['ps'] = getNameAndPS(job.name)[1]
        jobList.append(jobInfo)
    return jobList


def isVaildDate(date):
    try:
        if ":" in date:
            datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        else:
            datetime.strptime(date, "%Y-%m-%d")
        return True
    except:
        return False 


def scheduleHandler(msg):
    global dailyJson
    result = ''
    try:
        cmdList = msg.split()
        cmd = cmdList[0]
        #CQSDK.SendPrivateMsg(fromQQ, msg)
        if cmd == "行程命令":
            result += "行程列表\n"
            result += "添加行程\n"
            result += "删除行程\n"
            result += "今日行程群播报\n"
            result += "清空所有行程"

        if cmd == "日常命令":
            result += "设置日常任务\n"
            result += "清空日常任务\n"
            result += "查看日常任务\n"
            result += "设置日常提醒时间\n"
            result += "关闭日常提醒"


        if cmd == "添加行程":
            if len(cmdList) < 3:
                return '''命令格式错误：缺少参数
正确格式：添加行程 行程名称 行程日期 [行程时间 [备注]]
示例：
添加行程 TeamSII公演 2017-09-09 19:00:00 请前往口袋48或B站观看
添加行程 TeamSII公演 2017-09-09 19:00:00
添加行程 上海飞北京 2017-09-10
注意：[行程名称]中不能包含空格'''
            scheName = cmdList[1]
            if len(cmdList) == 3:
                scheTime = cmdList[2]
                isAlert = False
            else:
                scheTime = cmdList[2] + ' ' + cmdList[3]
                isAlert = True
                ps = ''
                for s in cmdList[4:]:
                    ps += s+' '
                nameAndPS = scheName + ' ' + ps
            if not isVaildDate(scheTime):
                return "时间格式错误，正确格式为 YYYY-MM-DD [HH:MM:SS]\n示例：\n2017-02-15\n2017-03-22 17:30:00"
            
            if isAlert:
                alertTime = datetime.strptime(scheTime, "%Y-%m-%d %H:%M:%S")
                alertTime = alertTime - alertDelta
            else:
                alertTime = datetime.strptime(scheTime, "%Y-%m-%d")
                alertTime = alertTime + timedelta(hours=23, minutes=59)
                nameAndPS = '*' + scheName #特殊标记区分
            scheduler.add_job(jobAlert, 'date', args=(nameAndPS, scheTime),
                run_date=alertTime, name=nameAndPS, coalesce=True)
            result = "成功添加行程：\n%s\n时间：%s"%(scheName, scheTime)

        if cmd == "删除行程":
            listAllJobs()
            if len(cmdList) == 1:
                if len(jobList) == 0:
                    result = '行程为空'
                else:
                    result = '请回复【删除行程 编号】删除指定行程：'
                    for job in jobList:
                        result += '\n[' + str(jobList.index(job) + 1) + ']'
                        result += '\n' + job['name']
                        result += '\n时间：' + job['time'] + '\n'
                    result = result.strip()
            elif len(cmdList) == 2:
                jobIdx = cmdList[1]
                if not jobIdx.isdigit() or int(jobIdx) <= 0:
                    return "数字格式错误：编号不是正整数"
                elif int(jobIdx) > len(jobList):
                    return "编号错误：超出最大编号"
                scheduler.remove_job(jobList[int(jobIdx)-1]['id'], jobstore='default')
                result = "成功删除行程：\n%s\n时间：%s"%(jobList[int(jobIdx)-1]['name'],
                    jobList[int(jobIdx)-1]['time'])

        if cmd == "行程列表":
            listAllJobs()
            result = '%s近期行程：'%(memberName)
            if len(jobList) == 0:
                result += '无'
            else:
                for job in jobList:
                    result += '\n' + job['name']
                    result += '\n时间：' + job['time'] + '\n'
                    if 'ps' in job and job['ps'] != '':
                        result += job['ps'] + '\n'
                result = result.strip()

        if cmd == "今日行程群播报":
            todayJob = getTodayJob()
            if todayJob == '无':
                result = '今日无行程，无法播报'
            else:
                text = '%s今日行程：'%(memberName)
                text += todayJob
                SendGroupMsgs(QQGroups, text)
                result = '已播报'

        if cmd == "清空所有行程":
            scheduler.remove_all_jobs(jobstore='default')
            result = "已清空"

        # =========================================================
        if cmd == "设置日常任务":
            if len(cmdList) == 1:
                return '''命令格式错误：缺少参数
正确格式：设置日常任务 任务描述
其中[任务描述]中的不同任务以空格或换行隔开'''
            dailyTask = '日常任务：'
            for task in cmdList[1:]:
                dailyTask += '\n' + task
            dailyJson['task'] = dailyTask
            saveJson(dailyJson, dailyTaskFN)
            result = "设置成功。输入[查看日常任务]显示任务"

        if cmd == "清空日常任务":
            dailyJson['task'] = ''
            saveJson(dailyJson, dailyTaskFN)
            result = '已清空'

        if cmd == "查看日常任务":
            if dailyJson['task']:
                result = dailyJson['task']
            else:
                result = '无任务'

        if cmd == "设置日常提醒时间":
            if len(cmdList) == 1:
                return '''设置格式：设置日常提醒时间 整点时间点
示例：
设置日常提醒时间 10,12,18
即在每天的10、12、18点整进行提醒
注意：
1.时间点为整数0-23，之间用英文逗号隔开
2.设置新的时间会覆盖之前的设置'''
            try:
                scheduler.remove_job('dailyAlert', jobstore='dailyStore')
            except Exception as e:
                pass

            try:
                scheduler.add_job(dailyAlert, 'cron', hour=cmdList[1], id='dailyAlert', 
                    jobstore='dailyStore')
            except Exception as e:
                return "时间格式错误"
            result = "设置成功。提醒时间：%s"%(cmdList[1])

        if cmd == "关闭日常提醒":
            try:
                scheduler.remove_job('dailyAlert', jobstore='dailyStore')
            except Exception as e:
                pass
            result = "已关闭。若重新开启请【设置日常提醒时间】"

    except Exception as e:
        print(e)
        return "程序错误：" + str(e)

    return result



from config import schedule_admins
QQGroups = schedule_admins.QQGroups
QQIds = schedule_admins.QQIds
QQGroups_daily = schedule_admins.QQGroups_daily
adminQQ = schedule_admins.adminQQ
memberName = schedule_admins.memberName
fansName = schedule_admins.fansName

jobDB = 'sqlite:///config/jobs.sqlite'
dailyDB = 'sqlite:///config/daily.sqlite'

# initial scheduler
jobstores = {
    'default': SQLAlchemyJobStore(url=jobDB),
    'dailyStore': SQLAlchemyJobStore(url=dailyDB),
    'memory': MemoryJobStore()
}
executors = {
    'default': ThreadPoolExecutor(30)
}
job_defaults = {
    'coalesce': True,
    'misfire_grace_time': 60
    # 'max_instances': 3
}

scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, 
    job_defaults=job_defaults)

scheduler.start()

dailyTaskFN = 'config/dailyTask.json'
dailyJson = loadJson(dailyTaskFN)
# 每日早9点播报当日行程
scheduler.add_job(morningHello, 'cron', hour=9, minute=0, jobstore='memory', coalesce=True)
# 添加监视器
scheduler.add_listener(my_listener)

alertDelta = timedelta(minutes=10)
# scheduler.remove_all_jobs()
qqbot.start()

print('行程管理已启动')


# 私聊消息
@qqbot.listener((RcvdPrivateMessage))
def ReplyRrivateMsg(message):
    result = ''
    if message.qq not in adminQQ:
        return
    result = scheduleHandler(message.text)
    if result:
        utils.reply(qqbot, message, result)

# 群消息
@qqbot.listener((RcvdGroupMessage))
def ReplyGroupMsg(message):
    result = ''
    if message.group not in []:
        return
    result = scheduleHandler(message.text)
    msg = "{text}\n{qq}".format(text=result, qq=CQAt(message.qq))
    if result:
        utils.reply(qqbot, message, msg)

while True:
    time.sleep(100)
