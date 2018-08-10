# -*- coding:utf-8 -*-
import os
import sys
sys.path.append('../lib')
from KD48API import KD48API
from utility import *

account = loadJson('../config/account.json')

api = KD48API()
res = api.login(account['id'], account['password'])
token = res['token']

allInfo = []
page = 1
while True:
    result = api.getHotRooms(token, page=page, groupId=0, needRootRoom=False)
    print('page:', page)
    hotRooms = result['data']
    if not hotRooms:
        break
    for memid in hotRooms:
        roomInfo = hotRooms[memid]
        currInfo = {}
        currInfo['groupId'] = roomInfo['groupId']
        currInfo['memberId'] = roomInfo['memberId']
        currInfo['memberName'] = roomInfo['memberName']
        currInfo['roomId'] = roomInfo['roomId']
        currInfo['voteMemberId'] = roomInfo['voteMemberId']
        allInfo.append(currInfo)
    page += 1

allInfo.append({"memberId": 63,"groupId": 0,"memberName": "袋王","roomId": 5774517,"voteMemberId": 0})

# print(allInfo)
print(len(allInfo))
saveJson(allInfo, '../data/MemberInfo.json')
