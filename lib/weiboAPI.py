# -*- coding:utf-8 -*-
import os
import re
import requests
import json
import logging
from datetime import datetime
import urllib.request as request
import urllib.parse as urlparse
from html.parser import HTMLParser
import login_weibocom
from hashlib import md5

from config import weibo_ID
gsid = weibo_ID.gsid
s = weibo_ID.s
gsid2 = weibo_ID.gsid2
s2 = weibo_ID.s2
username = weibo_ID.username
password = weibo_ID.password

class Weibo(object):
    def __init__(self):
        self.ss = requests.Session()
        self.weibocomSS = login_weibocom.login(username, password)

    def getSuperIDfromName(self, name):
        m = md5()
        m.update(name.encode('utf8'))
        return '100808' + m.hexdigest()

    def getStoryList(self):
        url = ( "https://api.weibo.cn/2/stories/home_list?networktype=wifi&moduleID=715"
                "&c=android&i=8477407&s={s}&ft=0&wm=14010_0013"
                "&aid=01AmyEY7V_Eaw1K6wS5z_5eLeIkcMEoeJUn37whx-R8tag9nc.&v_f=2"
                "&gsid={g}"
                "&lang=zh_CN&skin=default&oldwm=14010_0013&sflag=1").format(s=s, g=gsid)

        result = {}
        result['status'] = 1
        result['data'] = {}
        result['msg'] = ''

        try:
            res = self.ss.request('GET', url)
            j = res.json()
        except Exception as e:
            text = '获取微博故事失败！'
            logging.error(text)
            logging.exception(e)
            result['status'] = -100
            result['msg'] = text
            return result

        if 'errno' in j:
            logging.error(j['errmsg'])
            result['status'] = -2
            result['errno'] = j['errno']
            result['msg'] = j['errmsg']
            return result

        if 'story_list' not in j:
            result['status'] = -1
            result['msg'] = 'story_list keyword not exists!'
            return result

        storylist = j['story_list']

        # for story in storylist:
        #     if story['story']['owner']['id'] == mhid:
        #         story_id = story['story']['story_id']
        return storylist


    def getStory(self, story_id='3053424305_0'):
        url = ("https://api.weibo.cn/2/stories/details?networktype=wifi&extprops=%7B%7D&moduleID=715"
                "&c=android&i=8477407&s={s}&ft=0&wm=14010_0013&aid=01AmyEY7V_Eaw1K6wS5z_5eLeIkcMEoeJUn37whx-R8tag9nc."
                "&v_f=2&gsid={g}"
                "&lang=zh_CN&skin=default&type=0&oldwm=14010_0013&sflag=1&story_ids=").format(s=s, g=gsid)

        if not story_id.endswith('_0'):
            story_id += '_0'

        result = {}
        result['status'] = 1
        result['data'] = {}
        result['msg'] = ''

        urlstory = url + story_id

        try:
            res = self.ss.request('GET', urlstory)
            j = res.json()
        except Exception as e:
            text = '获取微博故事失败！'
            logging.error(text)
            logging.exception(e)
            result['status'] = -100
            result['msg'] = text
            return result

        if 'errno' in j:
            logging.error(j['errmsg'])
            result['status'] = -2
            result['errno'] = j['errno']
            result['msg'] = j['errmsg']
            return result

        storyInfo = []
        if 'story_details' not in j:
            result['status'] = -1
            result['msg'] = 'story_details keyword not exists!'
            return result

        story = j['story_details'][0]
        exist = story['story']['exist']
        nickname = story['story']['owner']['nickname']
        result['nickname'] = nickname
        if not exist:
            result['status'] = 0
            result['msg'] = nickname + ' 没有发布微博故事'
            return result

        story_id = story['story']['story_id']
        segments = story['story']['segments']
        for seg in segments:
            #seg['expire_time']
            segment_id = seg['segment_id']
            # create_time = seg['create_time']
            # if self.wbLastTime < create_time:
            #     self.wbLastTime = create_time
            resources = seg['resources']
            for res in resources:
                if res['resource_type'] == 2: # 视频封面图片
                    imgurl = res['hd_url']
                elif res['resource_type'] in [0,1]: #video or image
                    currstory = {}
                    currstory['type'] = res['resource_type']
                    currstory['url'] = res['hd_url']
                    currstory['duration'] = res['duration']
                    currstory['create_time'] = int(seg['create_time']) / 1000
                    currstory['comment_count'] = seg['comment_count'] if 'comment_count' in seg else ' '
                    currstory['play_count'] = seg['play_count'] if 'play_count' in seg else ' '
                    currstory['like_count'] = seg['like_count'] if 'like_count' in seg else ' '
                    currstory['share_count'] = seg['share_count'] if 'share_count' in seg else ' '
                    currstory['story_id'] = story_id
                    currstory['segment_id'] = segment_id
                    currstory['nickname'] = nickname
                    currstory['rank_text'] = seg['segment_rank']['text'] if 'segment_rank' in seg else '未上榜'
                    currstory['rank'] = seg['segment_rank']['rank'] if 'segment_rank' in seg else None
                    storyInfo.append(currstory)
        result['data'] = storyInfo
        result['status'] = 1
        result['msg'] = '成功获取微博故事'
        return result


    def analyzeStory(self, s):
        log = "视频地址：" + s['url'] + "\n"
        log += "视频时长：%.1fs"%(s['duration']/1000)
        return log


    def postStoryComment(self, comment, segment_id, story_id):
        url = ( "https://api.weibo.cn/2/stories/segment_comment_create?networktype=wifi&moduleID=715"
                "&wb_version=3512&c=android&i=8477407&s={s}&ft=0"
                "&ua=smartisan-SM919__weibo__7.11.3__android__android6.0.1&wm=14010_0013"
                "&aid=01AmyEY7V_Eaw1K6wS5z_5eLcz1fC23tLdoBt8M46jLhYfu0w.&v_f=2&v_p=55&from=107B395010"
                "&gsid={g}"
                "&lang=zh_CN&skin=default&oldwm=14010_0013&sflag=1").format(s=s2, g=gsid2)
        
        boundary = '------------1512801798608'
        head = {}
        head['Host'] = 'api.weibo.cn'
        head['Content-Type'] = 'multipart/form-data;boundary=%s'%boundary

        data = '''--------------1512801798608
Content-Disposition: form-data; name="comment"
Content-Type: text/plain;charset:"UTF-8"
Content-Transfer-Encoding: 8bit

%s
--------------1512801798608
Content-Disposition: form-data; name="reply"
Content-Type: text/plain;charset:"UTF-8"
Content-Transfer-Encoding: 8bit

0
--------------1512801798608
Content-Disposition: form-data; name="segment_id"
Content-Type: text/plain;charset:"UTF-8"
Content-Transfer-Encoding: 8bit

%s
--------------1512801798608
Content-Disposition: form-data; name="story_id"
Content-Type: text/plain;charset:"UTF-8"
Content-Transfer-Encoding: 8bit

%s
--------------1512801798608'''%(comment, segment_id, story_id)

        result = {}
        result['status'] = 1
        result['data'] = {}
        result['msg'] = ''

        try:
            res = self.ss.request('POST', url, data=data.encode('utf-8'), headers=head)
            j = res.json()
        except Exception as e:
            text = '评论微博故事失败！'
            logging.error(text)
            logging.exception(e)
            result['status'] = -1
            result['msg'] = text
            return result

        if 'errno' in j:
            logging.error(j['errmsg'])
            result['status'] = -1
            result['errno'] = j['errno']
            result['msg'] = j['errmsg']
            return result

        result['data'] = j
        result['status'] = 1
        result['msg'] = '评论成功'
        return result


    def getChaohuaStat(self, name):
        chaohuaID = self.getSuperIDfromName(name)
        url = 'https://weibo.com/p/%s/super_index'%(chaohuaID)
        header = {}
        # header['Host'] = 'weibo.com'
        # header['Connection'] = 'keep-alive'
        # header['Cache-Control'] = 'max-age=0'
        # header['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        # header['Upgrade-Insecure-Requests'] = '1'
        header['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0'
        # header['Accept-Encoding'] = 'gzip, deflate, sdch'
        # header['Accept-Language'] = 'zh-CN,zh;q=0.8'
        # header['Cookie'] = 'YF-Page-G0=8fee13afa53da91ff99fc89cc7829b07; SUB=_2AkMtMAf9f8NxqwJRmPETzW7rao5zzwnEieKbbPYmJRMxHRl-yT9kqhIEtRB6BrApEiUasol6dtZ0SZgScUxE2fBksmIa; SUBP=0033WrSXqPxfM72-Ws9jqgMF55529P9D9W52w0SWCbgjrbfA2c.D9Lk0'
        # header['Cookie'] = 'TC-V5-G0=10672b10b3abf31f7349754fca5d2248; TC-Page-G0=4c4b51307dd4a2e262171871fe64f295; WBStorage=c5ff51335af29d81|undefined; login_sid_t=8767d43d858aba5ed1b4279f1d35bc75; cross_origin_proto=SSL; TC-Ugrow-G0=e66b2e50a7e7f417f6cc12eec600f517; _s_tentry=weibo.com; Apache=8529576849573.597.1518972118867; SINAGLOBAL=8529576849573.597.1518972118867; ULV=1518972118874:1:1:1:8529576849573.597.1518972118867:; SSOLoginState=1518972130; SCF=AqUhPTLo21qZ5ETEMAJREdL-qe1qV5RoaayLauUpO-_sygWqRd6noEYum9qg9EVNZhkCSsBYDPqZDDzaE0eqBCQ.; SUB=_2A253jdyyDeRhGeNG41IY9CvPyjyIHXVU-0l6rDV8PUNbmtAKLWzXkW9NSwkAhjdxZS7s8GYfI95cOmYGgPkWzdFu; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WWM_ACQ10lhVKiF7EZgKNV65JpX5K2hUgL.Fo-R1h54Sh-0eK52dJLoIXnLxKqLBo-LB-2LxK.L1hML12eLxKqLBK5LB.eLxKqL1-eL1KMLxK-L1K-L122LxK-L1K-LBKqLxK-L1K-LBKqLxK-L1K-LBKqt; SUHB=0IIF-YV8Ugw1ff; ALF=1550508130; un=teamsii_ins@sina.com; wvr=6'
        class MyHTMLParser(HTMLParser):
            def __init__(self):
                HTMLParser.__init__(self)

            def handle_starttag(self, tag, attrs):   
                #print "Encountered the beginning of a %s tag" % tag   
                if tag == "meta":   
                    if len(attrs) == 0:   
                        pass   
                    else:
                        tmp = {}
                        for (variable, value) in attrs:
                            tmp[variable] = value
                        if 'name' in tmp and tmp['name'] == 'description':
                            self.content = tmp['content']

        try:
            res = self.weibocomSS.request('GET', url, headers=header)
            hp = MyHTMLParser()
            hp.feed(res.text)
            hp.close()
            data = re.findall(r"阅读:(\d+),帖子:(\d+),粉丝:(\d+)", hp.content)
            stat = {}
            stat['text'] = hp.content
            stat['viewCnt'] = int(data[0][0])
            stat['postCnt'] = int(data[0][1])
            stat['fansCnt'] = int(data[0][2])
            stat['date'] = str(datetime.now()).split('.')[0]
            stat['state'] = 1
            return stat
        except Exception as e:
            logging.exception(e)
            return None


    def checkInWeb(self, name):
        chaohuaID = self.getSuperIDfromName(name)
        url = ("https://weibo.com/p/aj/general/button?ajwvr=6&api=http://i.huati.weibo.com/aj/super/checkin"
              "&texta=%E7%AD%BE%E5%88%B0&textb=%E5%B7%B2%E7%AD%BE%E5%88%B0&status=0"
              "&id={id}&location=page_100808_super_index").format(id=chaohuaID)
        header = {}
        header['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0'
        stat = {}
        try:
            res = self.weibocomSS.request('GET', url, headers=header)
            j = res.json()
            # {'msg': '已签到', 'data': {'alert_title': '今日签到 第158名', 'tipMessage': '今日签到，经验值+4', 'alert_activity': '', 'alert_subtitle': '经验值+4'}, 'code': '100000'}
            # {'msg': '今天已签到', 'data': [], 'code': 382004}
            # {'msg': '请先关注再签到', 'data': [], 'code': 382003}
        except Exception as e:
            logging.exception(e)
            stat['state'] = -1
            return stat
        stat['time'] = str(datetime.now()).split('.')[0]
        stat['data'] = j['data']
        stat['msg'] = j['msg']
        if int(j['code']) == 100000:
            stat['check_count'] = int(re.findall(r"第(\d+)名", j['data']['alert_title'])[0])
            stat['state'] = 1
        else:
            stat['check_count'] = 0
            stat['state'] = 0
        return stat


    def checkInMobile(self, name):
        chaohuaID = self.getSuperIDfromName(name)
        url = ('http://mapi.weibo.com/2/page/button?request_url=http%3A%2F%2Fi.huati.weibo.com%2Fmobile%2Fsuper%2Factive_checkin%3F'
                'pageid%3D{id}&networktype=wifi&c=android&i=8477407&s={s}&ft=0'
                '&wm=14010_0013&aid=01AmyEY7V_Eaw1K6wS5z_5eLeIkcMEoeJUn37whx-R8tag9nc.&v_f=2&v_p=54'
                '&gsid={g}'
                '&lang=zh_CN&skin=default&oldwm=14010_0013&sflag=1').format(s=s, g=gsid, id=chaohuaID)

        data = {}
        data['status'] = 0
        try:
            res = self.ss.request('GET', url)
            j = res.json()
        except Exception as e:
            logging.exception(e)
            data['status'] = -1
            return data

        if 'result' not in j:
            data['status'] = -2
            return data

        # data = j
        # data['status'] = 1
        # msg = j['msg']
        if 'result' in j and j['result'] == '1':
            # data['rank'] = int(msg.split('第')[1].split('名')[0])
            scheme = j['scheme']
            url = scheme.split('url=')[-1]
            url = request.unquote(url)
            query = urlparse.urlparse(url).query
            querydict = urlparse.parse_qs(query)
            data['check_count'] = int(querydict['check_count'][0])
            data['check_days'] = int(querydict['check_int'][0])
            data['add_exp'] = int(querydict['int_ins'][0])
            data['status'] = 1
        else:
            data['check_count'] = 0
            data['status'] = -2

        return data


if __name__ == "__main__":
    w = Weibo()
    # r = w.getStory2()
    # r = w.getStory2('xxx')
    # r = w.getChaohuaStat()
    # print(r)

    # comment = '测试评论'
    # segment_id = '4184181225059656'
    # story_id = '3053424305_0'
    # r = w.postStoryComment(comment, segment_id, story_id)
    # print(r)
    os.system('pause')
