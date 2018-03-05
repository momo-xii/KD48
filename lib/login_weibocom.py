#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import base64
import rsa
import binascii
import requests
import re
import random
from urllib.parse import quote_plus, urlparse, parse_qs, unquote
# try:
#     from PIL import Image
# except:
#     pass

'''
如果没有开启登录保护，不用输入验证码就可以登录
如果开启登录保护，需要输入验证码
'''

# 构造 Request headers
agent = 'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:41.0) Gecko/20100101 Firefox/41.0'
headers = {
    'User-Agent': agent
}

session = requests.session()

# 访问 初始页面带上 cookie
index_url = "http://weibo.com/login.php"
try:
    session.get(index_url, headers=headers, timeout=2)
except:
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


# 预登陆获得 servertime, nonce, pubkey, rsakv
def get_server_data(su):
    pre_url = "http://login.sina.com.cn/sso/prelogin.php?entry=weibo&callback=sinaSSOController.preloginCallBack&su="
    pre_url = pre_url + su + "&rsakt=mod&checkpin=1&client=ssologin.js(v1.4.19)&_="
    pre_url = pre_url + str(int(time.time() * 1000))
    pre_data_res = session.get(pre_url, headers=headers)
    sever_data = eval(pre_data_res.content.decode("utf-8").replace("sinaSSOController.preloginCallBack", ''))
    return sever_data


def get_password(password, servertime, nonce, pubkey):
    rsaPublickey = int(pubkey, 16)
    key = rsa.PublicKey(rsaPublickey, 65537)  # 创建公钥
    message = str(servertime) + '\t' + str(nonce) + '\n' + str(password)  # 拼接明文js加密文件中得到
    message = message.encode("utf-8")
    passwd = rsa.encrypt(message, key)  # 加密
    passwd = binascii.b2a_hex(passwd)  # 将加密信息转换为16进制。
    return passwd


def get_cha(pcid):
    # 获得验证码
    cha_url = "http://login.sina.com.cn/cgi/pin.php?r="
    cha_url = cha_url + str(int(random.random() * 100000000)) + "&s=0&p="
    cha_url = cha_url + pcid
    cha_page = session.get(cha_url, headers=headers)
    with open("cha.jpg", 'wb') as f:
        f.write(cha_page.content)
        f.close()
    # try:
    #     im = Image.open("cha.jpg")
    #     im.show()
    #     im.close()
    # except:
    #     print("请到当前目录下，找到验证码后输入")


def loginM(data, showpin, pcid):
    login_url = 'http://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.19)'
    if showpin != 0:
        get_cha(pcid)
        data['door'] = input("请输入验证码（同目录下图片cha.jpg）：")
    login_page = session.post(login_url, data=data, headers=headers)
    login_loop = (login_page.content.decode("GBK"))
    pa = r'location\.replace\([\'"](.*?)[\'"]\)'
    loop_url = re.findall(pa, login_loop)[0]
    return loop_url


def login(username, password):
    # su 是加密后的用户名
    su = get_su(username)
    sever_data = get_server_data(su)
    servertime = sever_data["servertime"]
    nonce = sever_data['nonce']
    rsakv = sever_data["rsakv"]
    pubkey = sever_data["pubkey"]
    pcid = sever_data["pcid"]
    showpin = sever_data["showpin"]
    password_secret = get_password(password, servertime, nonce, pubkey)

    postdata = {
        'entry': 'weibo',
        'gateway': '1',
        'from': '',
        'savestate': '7',
        'useticket': '1',
        'pagerefer': "http://login.sina.com.cn/sso/logout.php?entry=miniblog&r=http%3A%2F%2Fweibo.com%2Flogout.php%3Fbackurl",
        'vsnf': '1',
        'pcid': pcid,
        'su': su,
        'service': 'miniblog',
        'servertime': servertime,
        'nonce': nonce,
        'pwencode': 'rsa2',
        'rsakv': rsakv,
        'sp': password_secret,
        'sr': '1366*768',
        'encoding': 'UTF-8',
        'prelt': '115',
        'url': 'http://weibo.com/ajaxlogin.php?framelogin=1&callback=parent.sinaSSOController.feedBackUrlCallBack',
        'returntype': 'META'
        }
    # loop_url: 包含登录是否成功的信息
    loop_url = loginM(postdata, showpin, pcid)
    query = parse_qs(urlparse(unquote(loop_url,encoding='gbk')).query)
    retcode = query['retcode'][0]

    # TODO
    # if retcode == '4049':
    #     # 为了您的帐号安全，请输入验证码
    #     reason = query['reason'][0]
    #     print(retcode+':', reason)
    #     showpin = 1
    #     loop_url = loginM(postdata, showpin, pcid)
    #     crossdomain2 = session.get(loop_url, headers=headers)
    #     # query = parse_qs(urlparse(unquote(loop_url,encoding='gbk')).query)
    #     # retcode = query['retcode'][0]

    if retcode == '0':
        # 登录成功
        pass
    else:
        reason = query['reason'][0]
        print(retcode+':', reason)
        if retcode == '4049':
            # 为了您的帐号安全，请输入验证码
            showpin = 1
            # loop_url = loginM(postdata, showpin, pcid)
        elif retcode == '2070':
            pass
            # 输入的验证码不正确
            # while retcode != '0':
            #     print(retcode+':', reason)
            #     print('验证码已刷新')
            #     loop_url = loginM(postdata, showpin, pcid)
            #     query = parse_qs(urlparse(unquote(loop_url,encoding='gbk')).query)
            #     retcode = query['retcode'][0]
        else:
            pass

    result = {}
    result['session'] = None
    result['uid'] = None
    try:
        login_index = session.get(loop_url, headers=headers)
        uuid = login_index.text
        uuid_pa = r'"uniqueid":"(.*?)"'
        uuid_res = re.findall(uuid_pa, uuid, re.S)[0]
        web_weibo_url = "http://weibo.com/%s/profile?topnav=1&wvr=6&is_all=1" % uuid_res
        weibo_page = session.get(web_weibo_url, headers=headers)
        weibo_pa = r'<title>(.*?)</title>'
        # print(weibo_page.content.decode("utf-8"))
        userID = re.findall(weibo_pa, weibo_page.content.decode("utf-8", 'ignore'), re.S)[0]
        result['session'] = session
        result['uid'] = uuid_res
        result['status'] = 1
    except Exception as e:
        result['status'] = -1
        # print('登录微博失败！')
    return result


if __name__ == "__main__":
    username = ""
    password = ""
    login(username, password)