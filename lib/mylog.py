# -*- coding:utf-8 -*-
import os
import logging
import time

currTime = time.strftime('%Y-%m-%d_%H-%M-%S',time.localtime(time.time()))
logDir = 'log'

try:
    os.mkdir(logDir)
except Exception as e:
    pass

def setLog(logFN='log', level=logging.WARNING):
    logging.basicConfig(
        level       = level,
        format      = '%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
        datefmt     = '%Y-%m-%d %H:%M:%S',
        filename    = os.path.join(logDir, '%s_%s.log'%(logFN, currTime)),
        filemode    = 'w+'
    )
