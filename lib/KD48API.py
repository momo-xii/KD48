# -*- coding:utf-8 -*-
import json
import requests
import time
import os
import logging
# import numpy as np

# python2 or python3
import sys
ver = sys.version_info
if ver.major == 2:
    import codecs
    import urllib as request
    reload(sys)
    sys.setdefaultencoding('utf-8')
else:
    import urllib.request as request

from utility import *

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

        # 代理设置
        self.proxy = {'https':'https://218.108.107.70:909'}
        self.useproxy = False

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
            if self.useproxy:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, proxies=self.proxy, timeout=5)
            else:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, timeout=5)
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
        result['msg'] = '成功获取热门房间列表'
        # logging.info('成功获取热门房间列表')
        return result

    # 分析热门房间是否有最新消息 TODO
    def analyzeHotRooms(self):
        pass

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
            if self.useproxy:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, proxies=self.proxy, timeout=5)
            else:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, timeout=5)
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
        result['data'] = {}
        result['msg'] = ''

        try:
            if self.useproxy:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, proxies=self.proxy, timeout=5)
            else:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, timeout=5)
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


    def analyzeMsg(self, message):
        '''
        分析并提取房间消息
        '''
        m = message
        ignore = False
        try:
            extInfo = json.loads(m['extInfo'])
            senderName = extInfo['senderName'] if 'senderName' in extInfo else ' '
            msgType = m['msgType']
            printText = ''
            bodys = ''

            if msgType == 0:
                # 文字消息
                if extInfo['messageObject'] == 'text':
                    # 普通消息
                    text = filter_emoji(extInfo['text'])
                    printText = senderName + '：' + text + '\n'
                elif extInfo['messageObject'] == 'faipaiText':
                    # 翻牌消息
                    faipaiName = filter_emoji(extInfo['faipaiName'])
                    faipaiContent = filter_emoji(extInfo['faipaiContent'])
                    text = filter_emoji(extInfo['messageText'])
                    printText += '聚聚\"' + faipaiName + '\"被翻牌啦！' + '\n'
                    printText += faipaiName + '：' + faipaiContent + '\n'
                    printText += senderName + '的回复：' + text + '\n'
                elif extInfo['messageObject'] == 'live' or extInfo['messageObject'] == 'diantai':
                    # 直播消息
                    ignore = True
                    text = filter_emoji(extInfo['referenceContent'])
                    printText += '直播消息：\n'
                    printText += text + '\n'
                    printText += '来自' + filter_emoji(extInfo['referenceTitle']) + '\n'
                elif extInfo['messageObject'] == 'deleteMessage':
                    ignore = True
                else:
                    printText = '未知类型文本消息：%s\n'%extInfo['messageObject']
            elif msgType == 1:
                # 图片消息
                bodys = json.loads(m['bodys'])
                url = bodys['url']
                ext = bodys['ext']
                printText += senderName + '发了一张图片\n'
                printText += '图片地址：' + url + '\n'
                printText += '图片格式：' + ext + '\n'
            elif msgType == 2:
                # 语音消息
                bodys = json.loads(m['bodys'])
                url = bodys['url']
                ext = bodys['ext']
                printText += senderName + '发了一条语音\n'
                printText += '语音地址：' + url + '\n'
                printText += '语音格式：' + ext + '\n'
            elif msgType == 3:
                # 视频消息
                bodys = json.loads(m['bodys'])
                url = bodys['url']
                ext = bodys['ext']
                printText += senderName + '发了一段视频\n'
                printText += '视频地址：' + url + '\n'
                printText += '视频格式：' + ext + '\n'
            else:
                printText = '未知格式消息：%d\n'%msgType
            printText += m['msgTimeStr']
        except Exception as e:
            printText = '房间消息解析错误！'
            logging.error(printText)
            logging.exception(e)

        msgInfo = {}
        msgInfo['messageObject'] = extInfo['messageObject'] if 'messageObject' in extInfo else ''
        msgInfo['ignore'] = ignore
        msgInfo['bodys'] = bodys
        msgInfo['printText'] = printText
        msgInfo['msgId'] = m['msgidClient'] if 'msgidClient' in m else None
        msgInfo['senderName'] = senderName
        msgInfo['senderAvatar'] = extInfo['senderAvatar'] if 'senderAvatar' in extInfo else None
        msgInfo['msgTime'] = m['msgTime'] if 'msgTime' in m else 0
        msgInfo['msgTimeStr'] = m['msgTimeStr'] if 'msgTime' in m else None
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
        result['liveList'] = {}
        result['reviewList'] = {}

        try:
            if self.useproxy:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, proxies=self.proxy, timeout=5)
            else:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, timeout=5)
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
        result['reviewList'] = j['content']['reviewList'] \
            if 'reviewList' in j['content'] else {}
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
            title = filter_emoji(live['title']) if 'title' in live else ' '
            subTitle = filter_emoji(live['subTitle']) if 'subTitle' in live else ' '
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
            if self.useproxy:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, proxies=self.proxy, timeout=5)
            else:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, timeout=5)
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
            title = filter_emoji(live['title']) if 'title' in live else ' '
            subTitle = filter_emoji(live['subTitle']) if 'subTitle' in live else ' '
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
            if self.useproxy:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, proxies=self.proxy, timeout=5)
            else:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, timeout=5)
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
        '''
        try:
            os.mkdir(downloadDir)
        except Exception as e:
            pass

        if msgInfo['msgType'] == 0:
            pass
        else:
            url = msgInfo['bodys']['url']
            ext = msgInfo['bodys']['ext']
            fn = os.path.join(downloadDir, msgInfo['msgTimeStr'] + '.' + ext)
            fn = fn.replace(':','-')
            try:
                request.urlretrieve(url, filename=fn)
            except Exception as e:
                return -1
            return 1


    def getAllMsgs(self, token, memberId, download=True, downloadDir='msgs', printMsg=False):
        '''
        获取某成员房间所有消息，并下载非文字类消息
        '''
        try:
            os.mkdir(downloadDir)
        except Exception as e:
            pass

        if ver.major == 2:
            f = codecs.open(os.path.join(downloadDir, 'msgs.txt'), 'w', 'utf8')
        else:
            f = open(os.path.join(downloadDir, 'msgs.txt'), 'w', encoding='utf8')

        res = self.getRoomInfo(token, memberId)
        roomInfo = res['data']
        roomId = roomInfo['roomId']

        #res = self.getRoomMsgs(token, roomId)
        msgs = ['1']#res['data']
        lastTime = 0#res['lastTime']

        while lastTime >= 0 and msgs:
            try:
                res = self.getRoomMsgs(token, roomId, lastTime=lastTime)
            except Exception as e:
                print(e)
            if res['status'] < 0:
                #msgs = []
                print(res['msg'])
                continue
            else:
                lastTime = res['lastTime']
                msgs = res['data']
            print(lastTime)
            for m in msgs:
                msgInfo = self.analyzeMsg(m)
                if printMsg:
                    print(msgInfo['printText']) #####
                f.write(msgInfo['printText'])
                f.write('\n')
                if msgInfo['msgType'] == 0:
                    pass
                else:
                    url = msgInfo['bodys']['url']
                    ext = msgInfo['bodys']['ext']
                    fn = os.path.join(downloadDir, msgInfo['msgTimeStr'] + '.' + ext)
                    fn = fn.replace(':','-')
                    if download:
                        request.urlretrieve(url, filename=fn)
                time.sleep(1)
        f.close()


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
            if self.useproxy:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, proxies=self.proxy, timeout=5)
            else:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, timeout=5)
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

        data = {"needRecommend":False,"needChatInfo":False,"needFriendsNum":False}

        result = {}
        result['status'] = 1
        result['msg'] = ''
        result['data'] = {}

        try:
            if self.useproxy:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, proxies=self.proxy, timeout=5)
            else:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, timeout=5)
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
            if self.useproxy:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, proxies=self.proxy, timeout=5)
            else:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, timeout=5)
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
            if self.useproxy:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, proxies=self.proxy, timeout=5)
            else:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, timeout=5)
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
            if self.useproxy:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, proxies=self.proxy, timeout=5)
            else:
                res = self.s.request('POST', url, data=json.dumps(data),
                                headers=head, timeout=5)
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
    api = KD48API()
    res = api.login('xxx','xxx')
    token = res['token']

    # res = api.getHotRooms(token, page=1, groupId=0, needRootRoom=False)
    # hotRooms = res['data']

    # memberId = 35
    # res = api.getRoomInfo(token, memberId)
    # roomInfo = res['data']

    # roomId = roomInfo['roomId']
    # res = api.getRoomMsgs(token, roomId)
    # msgs = res['data']

    # print(c(msgs))

    res = api.getOpenLiveList(token)
    liveList = res['liveList']
    reviewList = res['reviewList']
