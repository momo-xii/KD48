# -*- coding:utf-8 -*-  
# 定时检测程序是否还在运行，若没有运行则启动程序
import sys
import time
from datetime import datetime
import psutil
import subprocess

exeName = 'CQP.exe'
CMD = "D:\\测试机器人.lnk"
sleepTime = 15

def searchProgram(programName):
    exe_psutil = []
    for p in psutil.process_iter():
        try:
            if p.name() == programName:
                exe_psutil.append(p)
        except psutil.Error:
            pass
    return exe_psutil

if __name__ == "__main__":
    while True:
        foundProgram = searchProgram(exeName)
        if foundProgram == []:
            print("启动程序：%s"%(CMD))
            subprocess.Popen('start /B %s'%(CMD), shell=True)
            print(datetime.now())
        else:
            print("程序正在运行：")
            for p in foundProgram:
                print(p.exe())
            print(datetime.now())
        time.sleep(sleepTime)
