# -*- coding:utf-8 -*-
import os
import sys
import json
import requests
import time
import logging
import urllib.request as request
# import numpy as np

from utility import *
from cqsdk import CQImage, CQRecord
from MsgCounter import MsgCounter

# disable system proxy
os.environ['NO_PROXY'] = '48.cn'
# - The next line also works on global, but have side effect, see:
# - https://stackoverflow.com/questions/28521535/requests-how-to-disable-bypass-proxy 
# session.trust_env = False

# import ssl
# from functools import wraps
# def sslwrap(func):
#     @wraps(func)
#     def bar(*args, **kw):
#         kw['ssl_version'] = ssl.PROTOCOL_TLSv1
#         return func(*args, **kw)
#     return bar
# ssl.wrap_socket = sslwrap(ssl.wrap_socket)


class KD48API(object):
    def __init__(self):
        self.s = requests.Session()
        self.proxy = {}
        self.timeout = 10
        self.token = '0'

    def setProxy(self, proxy):
        self.proxy = proxy

    def getHeader(self):
        defaulthead = {}
        defaulthead['User-Agent'] = 'Mobile_Pocket'
        defaulthead['Content-Type'] = 'application/json;charset=utf-8'
        defaulthead['os'] = 'android'
        defaulthead['version'] = '5.1.1'
        defaulthead['Accept-Encoding'] = 'gzip'
        defaulthead['Connection'] = 'Keep-Alive'
        defaulthead['IMEI'] = '990033831321549'
        return defaulthead


    def login(self, account, password, type='ID'):
        '''
        登录并获取token
        type: ID, phone
        '''
        if type == 'ID':
            url = 'https://puser.48.cn/usersystem/api/user/v1/login/other/snh'
            data = {"password":password,"account":account,"nickname":account}
        elif type == 'phone':
            url = 'https://puser.48.cn/usersystem/api/user/v1/login/phone'
            data = {"password":password,"account":account}
        elif type == 'weibo':
            pass

        head = self.getHeader()
        head['Host'] = 'puser.48.cn'
        head['token'] = '0'

        result = {}
        result['status'] = 1
        result['token'] = '0'
        result['msg'] = ''

        try:
            res = self.s.request('POST', url, data=json.dumps(data),
                                   headers=head)
            j = res.json()
        except Exception as e:
            text = '网络阻塞！获取token失败！'
            logging.error(text)
            logging.exception(e)
            result['status'] = -1
            result['msg'] = text
            return result
        
        if j['status'] != 200:
            logging.error(j['message'])
            result['status'] = -1
            result['msg'] = j['message']
            return result

        result['content'] = j['content']
        result['token'] = j['content']['token']
        self.token = j['content']['token']
        result['userId'] = j['content']['userInfo']['userId']
        result['msg'] = '成功获取token'
        logging.info('成功获取token')
        return result


    def getHotRooms(self, token, page=1, groupId=0, needRootRoom=False):
        '''
        # 获取最新热门房间列表
        '''
        url = 'https://pjuju.48.cn/imsystem/api/im/v1/member/room/hot'
        head = self.getHeader()
        head['Host'] = 'pjuju.48.cn'
        head['token'] = token

        data = {"page":page,"groupId":groupId,"needRootRoom":needRootRoom}

        result = {}
        result['status'] = 1
        result['data'] = {}
        result['msg'] = ''

        try:
            res = self.s.request('POST', url, data=json.dumps(data),
                headers=head, proxies=self.proxy, timeout=self.timeout)
            j = res.json()
        except Exception as e:
            text = '获取热门房间列表失败！'
            logging.error(text)
            logging.exception(e)
            result['status'] = -1
            result['msg'] = text
            return result

        if j['status'] != 200:
            logging.error(j['message'])
            result['status'] = -1
            result['msg'] = j['message']
            return result

        hotRooms = {}
        roomInfo = j['content']['data']
        for room in roomInfo:
            room['lastCommentTime'] = ISOString2Time(room['lastCommentTime'])
            memberId = room['memberId']
            hotRooms[memberId] = room
        result['data'] = hotRooms
        result['roomList'] = roomInfo
        result['msg'] = '成功获取热门房间列表'
        return result

    # 分析热门房间是否有最新消息 TODO
    def analyzeHotRooms(self, token):
        res = self.getHotRooms(token, page=1, groupId=10)
        hotRooms = res['roomList']

    def getRoomInfo(self, token, memberId):
        '''
        获取成员房间基本信息
        return:
        roomInfo['roomId']
        roomInfo['roomName']
        roomInfo['topic']
        roomInfo['memberName']
        roomInfo['lastCommentTime'] (format time)
        roomInfo['roomAvatar']
        roomInfo['bgPath']
        '''
        url = 'https://pjuju.48.cn/imsystem/api/im/v1/member/room/info/memberId'
        sourceHost = 'https://source.48.cn'
        head = self.getHeader()
        head['Host'] = 'pjuju.48.cn'
        head['token'] = token

        data = {"memberId":memberId}

        result = {}
        result['status'] = 1
        result['data'] = {}
        result['msg'] = ''

        try:
            res = self.s.request('POST', url, data=json.dumps(data),
                headers=head, proxies=self.proxy, timeout=self.timeout)
            j = res.json()
        except Exception as e:
            text = '获取房间信息失败！'
            logging.error(text)
            logging.exception(e)
            result['status'] = -1
            result['msg'] = text
            return result

        if j['status'] != 200:
            logging.error(j['message'])
            result['status'] = -1
            result['msg'] = j['message']
            return result
        
        roomInfo = j['content']
        roomInfo['roomAvatar'] = sourceHost + roomInfo['roomAvatar'] \
            if 'roomAvatar' in roomInfo else ' '
        roomInfo['bgPath'] = sourceHost + roomInfo['bgPath'] \
            if 'bgPath' in roomInfo else ' '
        roomInfo['topic'] = roomInfo['topic'] if 'topic' in roomInfo else ' '
        roomInfo['roomName'] = roomInfo['roomName'] if 'roomName' in roomInfo else ' '

        result['data'] = roomInfo
        result['status'] = 1
        result['msg'] = '成功获取成员房间信息'
        # logging.info('成功获取成员房间信息')
        return result


    def getRoomMsgs(self, token, roomId, lastTime=0, limit=10):
        '''
        获取房间消息列表
        lastTime: 最早一条信息的时间，用于继续获取前一批消息
        limit: 每次获取信息的条数
        '''
        url = 'https://pjuju.48.cn/imsystem/api/im/v1/member/room/message/chat'
        head = self.getHeader()
        head['Host'] = 'pjuju.48.cn'
        head['token'] = token

        data = {"roomId":roomId,"lastTime":lastTime,"limit":limit}

        result = {}
        result['status'] = 1
        result['data'] = []
        result['msg'] = ''

        try:
            res = self.s.request('POST', url, data=json.dumps(data),
                headers=head, proxies=self.proxy, timeout=self.timeout)
            j = res.json()
        except Exception as e:
            text = '获取房间消息失败！'
            logging.error(text)
            logging.exception(e)
            result['status'] = -1
            result['msg'] = text
            return result

        if j['status'] != 200:
            logging.error(j['message'])
            result['status'] = -1
            result['msg'] = j['message']
            return result

        result['status'] = 1
        result['data'] = j['content']['data']
        result['lastTime'] = j['content']['lastTime']
        result['msg'] = '成功获取房间消息'
        return result


    def getRoomComments(self, token, roomId, lastTime=0, limit=10):
        '''
        获取房间留言列表
        lastTime: 最早一条信息的时间，用于继续获取前一批消息
        limit: 每次获取信息的条数
        '''
        url = 'https://pjuju.48.cn/imsystem/api/im/v1/member/room/message/comment'
        head = self.getHeader()
        head['Host'] = 'pjuju.48.cn'
        head['token'] = token

        data = {"roomId":roomId,"lastTime":lastTime,"limit":limit}

        result = {}
        result['status'] = 1
        result['data'] = []
        result['msg'] = ''

        try:
            res = self.s.post(url, data=json.dumps(data),
                headers=head, proxies=self.proxy, timeout=self.timeout)
            j = res.json()
        except Exception as e:
            text = '获取房间留言失败！'
            logging.error(text)
            logging.exception(e)
            result['status'] = -1
            result['msg'] = text
            return result

        if j['status'] != 200:
            logging.error(j['message'])
            result['status'] = -1
            result['msg'] = j['message']
            return result

        result['status'] = 1
        result['data'] = j['content']['data']
        result['lastTime'] = j['content']['lastTime']
        result['msg'] = '成功获取房间留言'
        return result


    def analyzeMsg(self, msg, CoolQRoot=''):
        '''
        分析并提取房间消息
        '''
        ignore = False
        msgInfo = msg
        try:
            extInfo = json.loads(msg['extInfo'])
            senderName = extInfo['senderName'] if 'senderName' in extInfo else ' '
            msgInfo['senderName'] = senderName
            msgType = msg['msgType']
            printText = ''
            bodys = ''
            try:
                bodys = json.loads(msg['bodys'])
            except Exception as e:
                pass
            msgInfo['bodys'] = bodys

            if msgType == 0:
                # 文字消息
                if extInfo['messageObject'] == 'text':
                    # 普通消息
                    text = extInfo['text']
                    printText = senderName + '：' + text + '\n'
                elif extInfo['messageObject'] == 'faipaiText':
                    # 翻牌消息
                    # 用userId查询nickName
                    faipaiContent = extInfo['faipaiContent']
                    faipaiNameAppear = True # 被翻牌聚聚名字是否出现
                    if faipaiNameAppear:
                        faipaiUserId = extInfo['faipaiUserId']
                        faipaiUserInfo = self.getUserInfo(self.token, faipaiUserId)
                        if faipaiUserInfo['status'] == 1:
                            faipaiName = faipaiUserInfo['data']['nickName']
                        else:
                            faipaiName = '某聚聚'
                            printText += '获取用户名失败\n'
                        printText += '聚聚“%s”被翻牌啦！'%(faipaiName) + '\n'
                        printText += '%s：'%(faipaiName) + faipaiContent + '\n'
                    else:
                        printText += '有聚聚被翻牌啦！' + '\n'
                        printText += '聚聚：' + faipaiContent + '\n'
                    text = extInfo['messageText']
                    printText += senderName + '的回复：' + text + '\n'
                elif extInfo['messageObject'] in ['live', 'diantai']:
                    # 直播消息
                    ignore = True
                    text = extInfo['referenceContent']
                    printText += '直播：' + text + '\n'
                    printText += '来自：' + extInfo['referenceTitle'] + '\n'
                elif extInfo['messageObject'] == 'idolFlip':
                    if extInfo['idolFlipType'] == 3:
                        extInfo['idolFlipUserName'] = '匿名聚聚'
                    printText += '%s翻牌了%s的问题\n'%(senderName, extInfo['idolFlipUserName'])
                    printText += '（具体问题与回答请前往口袋48房间查看）\n'
                elif extInfo['messageObject'] == 'deleteMessage':
                    ignore = True
                else:
                    printText = '未知类型文本消息：%s\n'%extInfo['messageObject']
            elif msgType == 1:
                # 图片消息
                printText += senderName + '发了一张图片\n'
                if CoolQRoot.strip() == '':
                    imgDLInfo = {}
                else:
                    CoolQImageDir = os.path.join(CoolQRoot, 'data', 'image')
                    imgDLInfo = self.downloadMsg(msgInfo, downloadDir=CoolQImageDir)
                if imgDLInfo:
                    CQImgText = '{cq}\n'.format(cq=CQImage(imgDLInfo['CoolQName']))
                    printText += CQImgText
                else:
                    printText += '图片地址：' + bodys['url'] + '\n'
                    printText += '图片格式：' + bodys['ext'] + '\n'
            elif msgType == 2:
                # 语音消息
                printText += senderName + '发了一条语音\n'
                if CoolQRoot.strip() == '':
                    recordDLInfo = {}
                else:
                    CoolQRecordDir = os.path.join(CoolQRoot, 'data', 'record')
                    recordDLInfo = self.downloadMsg(msgInfo, downloadDir=CoolQRecordDir)
                if recordDLInfo:
                    CQRecordText = '{cq}\n'.format(cq=CQRecord(recordDLInfo['CoolQName']))
                    printText += CQRecordText
                else:
                    printText += '语音地址：' + bodys['url'] + '\n'
                    printText += '语音格式：' + bodys['ext'] + '\n'
            elif msgType == 3:
                # 视频消息
                printText += senderName + '发了一段视频\n'
                printText += '视频地址：' + bodys['url'] + '\n'
                printText += '视频格式：' + bodys['ext'] + '\n'
            else:
                printText = '未知格式消息：%d\n'%msgType
            printText += msg['msgTimeStr']
        except Exception as e:
            printText = '房间消息解析错误！'
            logging.error(printText)
            logging.exception(e)

        msgInfo['extInfo'] = extInfo
        msgInfo['messageObject'] = extInfo['messageObject'] if 'messageObject' in extInfo else ''
        msgInfo['ignore'] = ignore
        msgInfo['printText'] = printText
        msgInfo['msgId'] = msg['msgidClient'] if 'msgidClient' in msg else None
        msgInfo['senderAvatar'] = extInfo['senderAvatar'] if 'senderAvatar' in extInfo else None
        msgInfo['msgTime'] = msg['msgTime'] if 'msgTime' in msg else 0
        msgInfo['msgTimeStr'] = msg['msgTimeStr'] if 'msgTime' in msg else None
        msgInfo['msgType'] = msgType
        msgInfo['senderId'] = int(extInfo['senderId']) if 'senderId' in extInfo else -1
        
        return msgInfo


    def getLiveList(self, token, memberId=0, groupId=0, liveType=0, 
                    lastTime=0, limit=20):
        '''
        获取成员直播列表
        memberId: 0 means all members
        groupId: 0 means all groups, SNH48: 10, BEJ48: 11, GNZ48: 12, SHY48: 13
        liveType: 0: all, 1: 视频, 2: 电台
        lastTime: 最早一条回放的时间，用于继续获取前一批回放
        limit: 每次获取信息的条数（回放条数，和直播无关）
        '''
        url = 'https://plive.48.cn/livesystem/api/live/v1/memberLivePage'
        head = self.getHeader()
        head['Host'] = 'plive.48.cn'
        head['token'] = token

        data = {"lastTime":lastTime,"groupId":groupId,"type":liveType,
                "memberId":memberId,"limit":limit}

        result = {}
        result['status'] = 1
        result['msg'] = ''
        result['liveList'] = []
        result['reviewList'] = []

        try:
            res = self.s.request('POST', url, data=json.dumps(data),
                headers=head, proxies=self.proxy, timeout=self.timeout)
            j = res.json()
        except Exception as e:
            text = '获取直播列表失败！'
            logging.error(text)
            logging.exception(e)
            result['status'] = -1
            result['msg'] = text
            return result
        
        if j['status'] != 200:
            logging.error(j['message'])
            result['status'] = -1
            result['msg'] = j['message']
            return result

        result['liveList'] = j['content']['liveList'] \
            if 'liveList' in j['content'] else []
        result['reviewList'] = j['content']['reviewList'] \
            if 'reviewList' in j['content'] else []
        result['status'] = 1
        result['msg'] = '成功获取直播列表'
        return result


    def getLiveInfo(self, live, isLive=True):
        '''
        分析并提取直播及回放信息
        isLive: 直播为True，回放为False
        '''
        sourceHost = 'https://source.48.cn'
        liveUrlhead = 'https://h5.48.cn/2017appshare/memberLiveShare/index.html?id='

        try:
            title = live['title'] if 'title' in live else ' '
            subTitle = live['subTitle'] if 'subTitle' in live else ' '
            streamPath = live['streamPath']
            liveUrl = liveUrlhead + live['liveId']
            startTime = live['startTime'] if 'startTime' in live else 0
            startTimeStr = time.strftime('%Y-%m-%d %H:%M:%S',
                                         time.localtime(startTime/1000))

            printText = ''
            if isLive:
                printText += "直播间：" + title.strip() + '\n'
                printText += "标题：" + subTitle.strip() + '\n'
                printText += "开始时间：" + startTimeStr + '\n'
                printText += "直播地址：" + liveUrl
                #printText += "视频地址：" + streamPath + '\n'
            else:
                printText += "直播间：" + title.strip() + '\n'
                printText += "标题：" + subTitle.strip() + '\n'
                printText += "开始时间：" + startTimeStr + '\n'
                printText += "在线观看：" + liveUrl + '\n'
                printText += "下载地址：" + streamPath
        except Exception as e:
            printText = "直播信息解析错误！"
            logging.error(printText)
            logging.exception(e)

        liveInfo = live
        liveInfo['printText'] = printText
        liveInfo['picPath'] = sourceHost + live['picPath'].replace(',', '\n'+sourceHost) \
            if 'picPath' in live else ' '
        liveInfo['lrcPath'] = sourceHost + live['lrcPath'] \
            if 'lrcPath' in live else ' '
        liveInfo['title'] = title
        liveInfo['subTitle'] = subTitle
        liveInfo['liveUrl'] = liveUrl
        liveInfo['startTimeStr'] = startTimeStr
        # liveInfo['streamPath'] = live['streamPath']
        # liveInfo['startTime'] = live['startTime']
        # liveInfo['liveId'] = live['liveId']
        # liveInfo['memberId'] = live['memberId']
        
        return liveInfo


    def getOpenLiveList(self, token, groupId=0, liveType=0, 
                    lastTime=0, lastGroupId=0, limit=20, isReview=0):
        '''
        获取公演直播列表
        groupId: 0 means all groups, SNH48: 10, BEJ48: 11, GNZ48: 12, SHY48: 13
        liveType: 0: all, 1: 视频, 2: 电台（需要确认）
        lastTime: 最早一条回放的时间，用于继续获取前一批回放
        limit: 每次获取信息的条数
        isReview: 0为直播，1为回放
        '''
        url = 'https://plive.48.cn/livesystem/api/live/v1/openLivePage'
        head = self.getHeader()
        head['Host'] = 'plive.48.cn'
        head['token'] = token

        data = {"isReview":isReview,"groupId":groupId,"lastGroupId":lastGroupId,
                "lastTime":lastTime,"type":liveType,"limit":limit}

        result = {}
        result['status'] = 1
        result['msg'] = ''
        result['liveList'] = {}

        try:
            res = self.s.request('POST', url, data=json.dumps(data),
                headers=head, proxies=self.proxy, timeout=self.timeout)
            j = res.json()
        except Exception as e:
            text = '获取直播列表失败！'
            logging.error(text)
            logging.exception(e)
            result['status'] = -1
            result['msg'] = text
            return result
        
        if j['status'] != 200:
            logging.error(j['message'])
            result['status'] = -1
            result['msg'] = j['message']
            return result

        result['liveList'] = j['content']['liveList'] \
            if 'liveList' in j['content'] else {}
        result['status'] = 1
        result['msg'] = '成功获取直播列表'
        return result


    def analyzeOpenLiveInfo(self, live, isLive=True):
        '''
        分析并提取直播及回放信息
        isLive: 直播为True，回放为False
        '''
        sourceHost = 'https://source.48.cn'
        liveUrlhead = 'https://h5.48.cn/2017appshare/liveshare/?id='

        try:
            title = live['title'] if 'title' in live else ' '
            subTitle = live['subTitle'] if 'subTitle' in live else ' '
            liveUrl = liveUrlhead + live['liveId']
            startTime = live['startTime'] if 'startTime' in live else 0
            startTimeStr = time.strftime('%Y-%m-%d %H:%M:%S',
                                         time.localtime(startTime/1000))

            printText = ''
            if isLive:
                printText += "标题：" + title.strip() + '\n'
                printText += "副标题：" + subTitle.strip() + '\n'
                printText += "开始时间：" + startTimeStr + '\n'
                if live['isOpen']:
                    printText += "正在直播中..."
            else:
                printText += "标题：" + title.strip() + '\n'
                printText += "副标题：" + subTitle.strip() + '\n'
                printText += "开始时间：" + startTimeStr + '\n'
        except Exception as e:
            printText = "直播信息解析错误！"
            logging.error(printText)
            logging.exception(e)

        liveInfo = live
        liveInfo['printText'] = printText.strip()
        liveInfo['picPath'] = sourceHost + live['picPath'].replace(',', '\n'+sourceHost) \
            if 'picPath' in live else ' '
        liveInfo['title'] = title
        liveInfo['subTitle'] = subTitle
        liveInfo['liveUrl'] = liveUrl
        liveInfo['startTimeStr'] = startTimeStr
        # liveInfo['startTime'] = live['startTime']
        # liveInfo['liveId'] = live['liveId']
        # liveInfo['isOpen'] = live['isOpen']
        
        return liveInfo


    def getOpenLiveOne(self, token, liveId, liveType=0):
        '''
        获取公演直播详细信息
        '''
        url = 'https://plive.48.cn/livesystem/api/live/v1/getLiveOne'
        head = self.getHeader()
        head['Host'] = 'plive.48.cn'
        head['token'] = token

        data =  {"type":liveType,"liveId":liveId}

        result = {}
        result['status'] = 1
        result['msg'] = ''
        result['data'] = {}

        try:
            res = self.s.request('POST', url, data=json.dumps(data),
                headers=head, proxies=self.proxy, timeout=self.timeout)
            j = res.json()
        except Exception as e:
            text = '获取直播列表失败！'
            logging.error(text)
            logging.exception(e)
            result['status'] = -1
            result['msg'] = text
            return result
        
        if j['status'] != 200:
            logging.error(j['message'])
            result['status'] = -1
            result['msg'] = j['message']
            return result

        result['data'] = j['content']
        result['status'] = 1
        result['msg'] = '成功获取直播列表'
        return result


    def downloadMsg(self, msgInfo, downloadDir='msgs'):
        '''
        下载非文字类消息
        每个成员单独一个文件夹
        CoolQName用于CoolQ的图片语音发送时的CQ码，CQ码路径不支持非gbk编码
        '''
        senderName = gbkIgnore(msgInfo['senderName'])
        downloadDir = os.path.join(downloadDir, senderName)
        try:
            os.makedirs(downloadDir)
        except Exception as e:
            pass

        result = {}
        if msgInfo['msgType'] == 0:
            pass
        else:
            url = msgInfo['bodys']['url']
            ext = msgInfo['bodys']['ext']
            fn = os.path.join(downloadDir, msgInfo['msgTimeStr'].replace(':','-') + '.' + ext)
            result['path'] = fn
            result['CoolQName'] = os.path.join(senderName, os.path.basename(fn))
            try:
                request.urlretrieve(url, filename=fn)
            except Exception as e:
                text = '下载失败！'
                logging.error(text)
                logging.exception(e)
                return {}
            result['status'] = 1
            return result


    def getAllMsgs(self, token, memberId, download=True, downloadDir='msgs', 
        printMsg=False, lastTime=0, dateLimit='2017-01-01'):
        '''
        获取某成员房间所有消息，并下载非文字类消息
        '''
        try:
            os.makedirs(downloadDir)
        except Exception as e:
            pass

        textFN = 'msgs.txt'
        f = open(os.path.join(downloadDir, textFN), 'w', encoding='utf8')
        res = self.getRoomInfo(token, memberId)
        if res['status'] < 0:
            print(res['msg'])
            return
        roomId = res['data']['roomId']

        msgs = ['1']
        lastTime = lastTime
        msgCounter = MsgCounter(memberId)
        timeLimit = ISOTime2Timestamp(dateLimit + ' 00:00:00')
        while lastTime >= 0 and msgs:
            res = self.getRoomMsgs(token, roomId, lastTime=lastTime, limit=100)
            if res['status'] < 0:
                print(res['msg'])
                continue
            lastTime = res['lastTime']
            msgs = res['data']
            for m in msgs:
                if m['msgTime']/1000 < timeLimit:
                    break
                msgInfo = self.analyzeMsg(m)
                msgCounter.counter(msgInfo)
                if printMsg:
                    print(msgInfo['printText']) #cmd窗口不支持输出非gbk字符
                f.write(msgInfo['printText'].strip())
                f.write('\n\n')
                # 统计字数使用，只有发言和翻牌的原始文字
                # if msgInfo['msgType'] == 0 and not msgInfo['ignore']:
                #     if 'text' in msgInfo['extInfo']:
                #         f.write(msgInfo['extInfo']['text'])
                #         f.write('\n\n')
                #     elif 'messageText' in msgInfo['extInfo']:
                #         f.write(msgInfo['extInfo']['messageText'])
                #         f.write('\n\n')
                if download:
                    self.downloadMsg(msgInfo, downloadDir=downloadDir)
            print(msgCounter.info())
            print('Next timestamp:', lastTime)
            if lastTime/1000 < timeLimit:
                print('已到截止时间：', dateLimit)
                break
            time.sleep(2)
        f.close()
        print('统计完毕，结果为：')
        print(msgCounter.info())


    def checkIn(self, token):
        '''
        打卡签到
        '''
        url = 'https://puser.48.cn/usersystem/api/user/v1/check/in'
        head = self.getHeader()
        head['Host'] = 'puser.48.cn'
        head['token'] = token

        data = {}

        result = {}
        result['status'] = 1
        result['msg'] = ''

        try:
            res = self.s.request('POST', url, data=json.dumps(data),
                headers=head, proxies=self.proxy, timeout=self.timeout)
            j = res.json()
        except Exception as e:
            text = '签到失败！'
            logging.error(text)
            logging.exception(e)
            result['status'] = -1
            result['msg'] = text
            return result
        
        if j['status'] != 200:
            logging.error(j['message'])
            result['status'] = -1
            result['msg'] = j['message']
            return result

        result['status'] = 1
        result['msg'] = '签到成功'
        return result


    def getUserInfo(self, token, userId):
        '''
        获取用户信息
        '''
        url = 'https://puser.48.cn/usersystem/api/user/v1/show/info/%d'%userId
        head = self.getHeader()
        head['Host'] = 'puser.48.cn'
        head['token'] = token

        data = {"needRecommend":True,"needChatInfo":True,"needFriendsNum":True}

        result = {}
        result['status'] = 1
        result['msg'] = ''
        result['data'] = {}

        try:
            res = self.s.request('POST', url, data=json.dumps(data),
                headers=head, proxies=self.proxy, timeout=self.timeout)
            j = res.json()
        except Exception as e:
            text = '获取用户信息失败！'
            logging.error(text)
            logging.exception(e)
            result['status'] = -1
            result['msg'] = text
            return result
        
        if j['status'] != 200:
            logging.error(j['message'])
            result['status'] = -1
            result['msg'] = j['message']
            return result

        result['data'] = j['content']['userInfo']
        result['status'] = 1
        result['msg'] = '成功获取用户信息'
        return result


    def shareLive(self, token, userId, resId):
        '''
        分享成员直播（用于获取经验值）
        userId: 用户的id
        resId: 直播的id，即liveId
        '''
        url = 'https://plive.48.cn/livesystem/api/live/v1/memberLiveShare'
        head = self.getHeader()
        head['Host'] = 'plive.48.cn'
        head['token'] = token

        data = {"userId":userId,"resId":resId}

        result = {}
        result['status'] = 1
        result['msg'] = ''

        try:
            res = self.s.request('POST', url, data=json.dumps(data),
                headers=head, proxies=self.proxy, timeout=self.timeout)
            j = res.json()
        except Exception as e:
            text = '分享成员直播失败！'
            logging.error(text)
            logging.exception(e)
            result['status'] = -1
            result['msg'] = text
            return result
        
        if j['status'] != 200:
            logging.error(j['message'])
            result['status'] = -1
            result['msg'] = j['message']
            return result

        result['status'] = 1
        result['msg'] = '成功分享成员直播'
        return result


    def getWeiboList(self, token, userId, memberId, limit=10):
        '''
        获取成员微博同步列表
        '''
        url = 'https://pdynamic.48.cn/dynamicsystem/api/dynamic/v1/list/member/%d'%(memberId)
        head = self.getHeader()
        head['Host'] = 'pdynamic.48.cn'
        head['token'] = token

        data = {"lastTime":0,"userId":userId,"limit":limit}

        result = {}
        result['status'] = 1
        result['msg'] = ''
        result['data'] = {}

        try:
            res = self.s.request('POST', url, data=json.dumps(data),
                headers=head, proxies=self.proxy, timeout=self.timeout)
            j = res.json()
        except Exception as e:
            text = '获取用户微博列表失败！'
            logging.error(text)
            logging.exception(e)
            result['status'] = -1
            result['msg'] = text
            return result
        
        if j['status'] != 200:
            logging.error(j['message'])
            result['status'] = -1
            result['msg'] = j['message']
            return result

        result['data'] = j['content']
        result['status'] = 1
        result['msg'] = '成功获取用户微博列表'
        return result


    def praiseWeibo(self, token, resId):
        '''
        点赞口袋中同步的微博
        resId: 微博的id
        '''
        url = 'https://pdynamic.48.cn/dynamicsystem/api/dynamic/v1/praise'
        head = self.getHeader()
        head['Host'] = 'pdynamic.48.cn'
        head['token'] = token
        # n = np.random.randint(10000000, 99999999) 
        # imei = '8964190'+str(n)
        # head['IMEI'] = imei

        data = {"resId":resId}

        result = {}
        result['status'] = 1
        result['msg'] = ''

        try:
            res = self.s.request('POST', url, data=json.dumps(data),
                headers=head, proxies=self.proxy, timeout=self.timeout)
            j = res.json()
        except Exception as e:
            text = '点赞微博失败！'
            logging.error(text)
            logging.exception(e)
            result['status'] = -1
            result['msg'] = text
            return result
        
        if j['status'] != 200:
            logging.error(j['message'])
            result['status'] = -1
            result['msg'] = j['message']
            return result

        result['status'] = 1
        result['msg'] = '成功点赞微博'
        return result


if __name__ == "__main__":
    account = loadJson('./config/account.json')
    api = KD48API()
    res = api.login(account['id'], account['password'])
    token = res['token']

    # liveList = api.getLiveList(token)
    # print(liveList)

    # msgs = api.getRoomMsgs(token, roomId=5780841, lastTime=0, limit=10)
    # for m in reversed(msgs['data']):
    #     import pdb
    #     pdb.set_trace()
    #     msg = api.analyzeMsg(m)
    #     print(gbkIgnore(msg['printText']))

    # res1 = api.getUserInfo(token, 398534)
    # print(res1)
    res = api.getHotRooms(token, page=1, groupId=0, needRootRoom=True)
    hotRooms = res['roomList']
    print(gbkIgnore(str(hotRooms)))

    # memberId = 35
    # res = api.getRoomInfo(token, memberId)
    # roomInfo = res['data']

    # roomId = roomInfo['roomId']
    # res = api.getRoomMsgs(token, roomId)
    # msgs = res['data']

    # print(c(msgs))

    # res = api.getOpenLiveList(token)
    # liveList = res['liveList']
    # reviewList = res['reviewList']
