# -*- coding:utf-8 -*-
import os
import sys
import time
import re
import threading
import subprocess
import urllib.request
sys.path.append('./lib')
from KD48API import KD48API
from utility import *
from apscheduler.schedulers.background import BackgroundScheduler

import logging
import mylog
mylog.setLog('memberLiveDL')

import ssl
ssl._create_default_https_context = ssl._create_unverified_context


memberId = [35]#,63,5973]

videoDir = "D:/video/snh/live/"
if not os.path.exists(videoDir):
    os.makedirs(videoDir)

postProc = False

def report(count, blockSize, totalSize):
    percent = count*blockSize*100/totalSize
    sys.stdout.write("\r下载进度：%.1f%%" % percent)
    sys.stdout.flush()


def DLandRemux(url, path):
    useFFmpeg = True
    if url.endswith('.mp4'):
        useFFmpeg = False
        try:
            urllib.request.urlretrieve(url, path, reporthook=report)
            print('')
        except Exception as e:
            print(e)
            useFFmpeg = True
    else:
        useFFmpeg = True

    if useFFmpeg:
        cmd1 = 'powershell ffmpeg -i "%s" -c copy "%s"'%(url, path)
        if postProc:
            remuxFN = path + '-remux.mp4'
            cmd2 = 'powershell ffmpeg -i "%s" -c:v libx264 -b:v 1100000 -c:a aac -b:a 64000 "%s"'%(path, remuxFN)
            cmd = cmd1 + ' ; ' + cmd2
        else:
            cmd = cmd1
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        if postProc:
            remuxFN = path + '-remux.mp4'
            cmd = 'powershell ffmpeg -i "%s" -c:v libx264 -b:v 1100000 -c:a aac -b:a 64000 "%s"'%(path, remuxFN)
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)


def DLandRotate(url, path):
    if url.startswith('rtmp'):
        cmd1 = 'powershell ffmpeg -i "%s" -c copy "%s"'%(url, path)
        if postProc:
            remuxFN = path + '-rotate.mp4'
            cmd2 = 'powershell ffmpeg -i "%s" -vf "transpose=2" -c:v libx264 -b:v 1750000 -c:a copy "%s"'%(path, remuxFN)
            cmd = cmd1 + ' ; ' + cmd2
        else:
            cmd = cmd1
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        cmd = 'powershell ffmpeg -i "%s" -c copy "%s"'%(url, path)
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)


def run():
    api = KD48API()
    token = '0'

    oldLiveIds = []
    oldReviewIds = []

    # initial
    res = api.getLiveList(token, limit=50)
    if res['status'] < 0:
        print('Connection Error!')
        sys.exit()

    liveList = res['liveList']
    reviewList = res['reviewList']
    if liveList:
        for live in reversed(liveList):
            oldLiveIds.append(live['liveId'])
    if reviewList:
        for review in reversed(reviewList):
            oldReviewIds.append(review['liveId'])


    def downloadLive():
        res = api.getLiveList(token, limit=30)
        if res['status'] != -1:
            liveList = res['liveList']
            reviewList = res['reviewList']

        for live in reversed(liveList):
            if live['liveId'] not in oldLiveIds:
                oldLiveIds.append(live['liveId'])
                if live['memberId'] in memberId or 0 in memberId:
                    liveInfo = api.getLiveInfo(live, True)
                    log = live['title'] + "开始直播了！\n"
                    log += liveInfo['printText']
                    print(gbkIgnore(log))
                    # 录制直播
                    fn = '直播 ' + live['title'] + ' ' + live['startTimeStr'].replace(':','')
                    # fn += ' ' + live['subTitle'].strip()
                    fn = re.sub('[\/:*?"<>|&\n\r]','-',fn)
                    fn = gbkIgnore(fn)
                    fn = fn.replace(' ', '_')
                    if len(fn) > 160:
                        fn = fn[0:160]
                    if not fn.endswith('.mp4'):
                        fn += '.mp4'
                    streamPath = liveInfo['streamPath']
                    print('直播流：', streamPath)
                    print('保存名称：', fn)
                    # cmd = "powershell -WindowStyle Hidden -command \"& { iwr %s -OutFile %s }\""%(
                    #     streamPath, os.path.join(videoDir+fn))
                    dl_thread = threading.Thread(target=DLandRotate, args=(streamPath, 
                        os.path.join(videoDir,fn),), daemon=True)
                    dl_thread.start()
                    print('\n')
        if not liveList:
            del oldLiveIds[:]

        for review in reversed(reviewList):
            if review['liveId'] not in oldReviewIds:
                if review['liveId'] in oldLiveIds:
                    oldLiveIds.remove(review['liveId'])
                oldReviewIds.append(review['liveId'])
                oldReviewIds.pop(0)
                if review['memberId'] in memberId or 0 in memberId:
                    liveInfo = api.getLiveInfo(review, False)
                    log = review['title'] + "的最新直播回放已出！\n"
                    log += liveInfo['printText']
                    print(gbkIgnore(log))
                    fn = '回放 ' + review['title'] + ' ' + review['startTimeStr'].replace(':','')
                    # fn += ' ' + review['subTitle'].strip()
                    fn = re.sub('[\/:*?"<>|&\n\r]','-',fn)
                    fn = gbkIgnore(fn)
                    fn = fn.replace(' ', '_')
                    if len(fn) > 160:
                        fn = fn[0:160]
                    if not fn.endswith('.mp4'):
                        fn += '.mp4'
                    streamPath = liveInfo['streamPath']
                    print('保存名称：', fn)
                    # cmd = "powershell -WindowStyle Hidden -command \"& { iwr %s -OutFile %s }\""%(
                    #     streamPath, os.path.join(videoDir+fn))
                    dl_thread = threading.Thread(target=DLandRemux, args=(streamPath, 
                        os.path.join(videoDir,fn),), daemon=True)
                    dl_thread.start()
                    print('\n')


    scheduler = BackgroundScheduler()

    scheduler.add_job(downloadLive, 'interval', seconds=5, id='download', 
        misfire_grace_time=3, coalesce=True)

    scheduler.start()
    print('开始监控直播下载...')
    print('监控成员编号：', memberId)


if __name__ == "__main__":
    run()
    while True:
        time.sleep(100)
