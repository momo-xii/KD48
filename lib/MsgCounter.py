# -*- coding:utf-8 -*-

class MsgCounter(object):
    def __init__(self, memberId=0):
        self.memberId = memberId
        self.msgCnt = 0
        self.msgTextCnt = 0
        self.msgImgCnt = 0
        self.msgAudioCnt = 0
        self.msgVideoCnt = 0

    def reset(self):
        self.msgCnt = 0
        self.msgTextCnt = 0
        self.msgImgCnt = 0
        self.msgAudioCnt = 0
        self.msgVideoCnt = 0

    def counter(self, msg):
        if msg['senderId'] != self.memberId:
            return
        if msg['ignore']:
            return
        currType = msg['msgType']
        self.msgCnt += 1
        if currType == 0:
            self.msgTextCnt += 1
        if currType == 1:
            self.msgImgCnt += 1
        if currType == 2:
            self.msgAudioCnt += 1
        if currType == 3:
            self.msgVideoCnt += 1

    def info(self):
        log = "本次总共发了%d条消息\n" % (self.msgCnt)
        log += "其中："
        if self.msgTextCnt > 0:
            log += "\n文字消息：%d" % self.msgTextCnt
        if self.msgImgCnt > 0:
            log += "\n图片消息：%d" % self.msgImgCnt
        if self.msgAudioCnt > 0:
            log += "\n语音消息：%d" % self.msgAudioCnt
        if self.msgVideoCnt > 0:
            log += "\n视频消息：%d" % self.msgVideoCnt
        return log
