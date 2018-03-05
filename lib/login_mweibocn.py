#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import re
import json
import base64
import time
import math
import random
# from PIL import Image
from urllib.parse import quote_plus

# 构造 Request headers
agent = 'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.110 Safari/537.36'
global headers
headers = {
    # "Host": "passport.weibo.cn",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    'User-Agent': agent
}

session = requests.session()
# 访问登录的初始页面
index_url = "https://passport.weibo.cn/signin/login"
session.get(index_url, headers=headers)


def get_su(username):
    """
    对 email 地址和手机号码 先 javascript 中 encodeURIComponent
    对应 Python 3 中的是 urllib.parse.quote_plus
    然后在 base64 加密后decode
    """
    username_quote = quote_plus(username)
    username_base64 = base64.b64encode(username_quote.encode("utf-8"))
    return username_base64.decode("utf-8")


# 处理验证码
def login_pre(username):
    # 采用构造参数的方式
    params = {
        "checkpin": "1",
        "entry": "mweibo",
        "su": get_su(username),
        "callback": "jsonpcallback" + str(int(time.time() * 1000) + math.floor(random.random() * 100000))
    }
    pre_url = "https://login.sina.com.cn/sso/prelogin.php"
    # headers["Host"] = "login.sina.com.cn"
    headers["Referer"] = index_url
    pre = session.get(pre_url, params=params, headers=headers)
    pa = r'\((.*?)\)'
    res = re.findall(pa, pre.text)
    if res == []:
        print("好像哪里不对了哦，请检查下你的网络，或者你的账号输入是否正常")
    else:
        js = json.loads(res[0])
        if js["showpin"] == 1:
            # headers["Host"] = "passport.weibo.cn"
            capt = session.get("https://passport.weibo.cn/captcha/image", headers=headers)
            capt_json = capt.json()
            capt_base64 = capt_json['data']['image'].split("base64,")[1]
            with open('capt.jpg', 'wb') as f:
                f.write(base64.b64decode(capt_base64))
                f.close()
            # im = Image.open("capt.jpg")
            # im.show()
            # im.close()
            cha_code = input("请输入验证码：>")
            return cha_code, capt_json['data']['pcid']
        else:
            return ""


def login(username, password):
    pincode = login_pre(username)
    postdata = {
        "username": username,
        "password": password,
        "savestate": "1",
        "ec": "0",
        "pagerefer": "",
        "entry": "mweibo",
        "wentry": "",
        "loginfrom": "",
        "client_id": "",
        "code": "",
        "qq": "",
        "hff": "",
        "hfp": "",
    }
    if pincode == "":
        pass
    else:
        postdata["pincode"] = pincode[0]
        postdata["pcid"] = pincode[1]
    # headers["Host"] = "passport.weibo.cn"
    headers["Reference"] = index_url
    headers["Origin"] = "https://passport.weibo.cn"
    headers["Content-Type"] = "application/x-www-form-urlencoded"

    post_url = "https://passport.weibo.cn/sso/login"
    login = session.post(post_url, data=postdata, headers=headers)
    # cookies 中的 SUB 即为 gsid
    # print('cookies:', login.cookies)
    # gsid = login.cookies['SUB']
    # print(login.status_code)
    result = {}
    result['session'] = None
    result['uid'] = None
    result['msg'] = ''
    js = login.json()
    if js['retcode'] != 20000000:
        print(js['msg'])
        result['status'] = -1
        result['msg'] = js['msg']
        return result
    # print('js:',js)
    uid = js["data"]["uid"]
    result['uid'] = uid
    result['session'] = session
    result['status'] = 1
    # crossdomain = js["data"]["crossdomainlist"]
    # cn = crossdomain["sina.com.cn"]
    # mcn = crossdomain["weibo.cn"]
    # com = crossdomain['weibo.com']
    # session.get(cn, headers=headers)
    # ht = session.get("http://weibo.cn/%s/info" % uid, headers=headers)
    # print(session.cookies)
    # pa = r'<title>(.*?)</title>'
    # res = re.findall(pa, ht.text)
    # print("你好%s，你正在使用 xchaoinfo 写的模拟登录" % res[0])
    return result


if __name__ == "__main__":

    username = ""
    password = ""
    # pincode = login_pre(username)
    login(username, password)