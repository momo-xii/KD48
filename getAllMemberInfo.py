# -*- coding:utf-8 -*-
import os
from KD48API import KD48API
from utility import *

account = loadJson('./config/account.json')

api = KD48API()
res = api.login(account['id'], account['password'])
token = res['token']

allInfo = []
page = 1
while True:
    result = api.getHotRooms(token, page=page, groupId=0, needRootRoom=False)
    print(page)
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
        allInfo.append(currInfo)
    page += 1

allInfo.append({"memberId": 63,"groupId": 0,"memberName": "袋王","roomId": 5774517})

print(allInfo)
print(len(allInfo))
saveJson(allInfo, './data/MemberInfo.json')

# 从alInfo中筛选
# 筛选特定成员
res = list(filter(lambda x:x['memberName'] == '莫寒', allInfo))
# 筛选groupId为10的成员，即SNH48的成员
res = list(filter(lambda x:x['groupId'] == 10, allInfo))
