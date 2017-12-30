# -*- coding:utf-8 -*-
import os
import requests
import json
import logging
from datetime import datetime
import urllib.request as request
import urllib.parse as urlparse

from config import weibo_ID
gsid = weibo_ID.gsid
s = weibo_ID.s
gsid2 = weibo_ID.gsid2
s2 = weibo_ID.s2
chid = weibo_ID.chid
containerid = weibo_ID.containerid

class Weibo(object):
    def __init__(self):
        self.ws = requests.Session()
        self.wbLastTime = 0
        self.fansCntLast = 0
        self.postCntLast = 0
        cntInfo = self.getDataInfo()
        if cntInfo:
            if 'errno' in cntInfo and cntInfo['errno'] < 0:
                pass
            else:
                self.fansCntLast = cntInfo['fansCnt']
                self.postCntLast = cntInfo['postCnt']


    def getStory(self):
        url = ( "https://api.weibo.cn/2/stories/home_list?networktype=wifi&moduleID=715"
                "&c=android&i=8477407&s={s}&ft=0&wm=14010_0013"
                "&aid=01AmyEY7V_Eaw1K6wS5z_5eLeIkcMEoeJUn37whx-R8tag9nc.&v_f=2"
                "&gsid={g}"
                "&lang=zh_CN&skin=default&oldwm=14010_0013&sflag=1").format(s=s, g=gsid)

        url2 = ("https://api.weibo.cn/2/stories/details?networktype=wifi&extprops=%7B%7D&moduleID=715"
                "&c=android&i=8477407&s={s}&ft=0&wm=14010_0013&aid=01AmyEY7V_Eaw1K6wS5z_5eLeIkcMEoeJUn37whx-R8tag9nc."
                "&v_f=2&gsid={g}"
                "&lang=zh_CN&skin=default&type=0&oldwm=14010_0013&sflag=1&story_ids=").format(s=s, g=gsid)

        storyExist = False

        result = {}
        result['status'] = 1
        result['data'] = {}
        result['msg'] = ''

        try:
            res = self.ws.request('GET', url)
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

        for story in storylist:
            if story['story']['owner']['id'] == mhid:
                story_id = story['story']['story_id']
                storyExist = True

        if not storyExist:
            result['status'] = 0
            result['msg'] = '没有发布微博故事'
            return result

        urlstory = url2 + story_id

        try:
            res = self.ws.request('GET', urlstory)
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
                    currstory['comment_count'] = seg['comment_count']
                    currstory['play_count'] = seg['play_count']
                    currstory['like_count'] = seg['like_count']
                    currstory['share_count'] = seg['share_count']
                    currstory['story_id'] = story_id
                    currstory['segment_id'] = segment_id
                    currstory['rank_text'] = seg['segment_rank']['text'] if 'segment_rank' in seg else None
                    currstory['rank'] = seg['segment_rank']['rank'] if 'segment_rank' in seg else None
                    storyInfo.append(currstory)
        result['data'] = storyInfo
        result['status'] = 1
        result['msg'] = '成功获取微博故事'
        return result


    def getStory2(self, story_id='3053424305_0'):
        url2 = ("https://api.weibo.cn/2/stories/details?networktype=wifi&extprops=%7B%7D&moduleID=715"
                "&c=android&i=8477407&s={s}&ft=0&wm=14010_0013&aid=01AmyEY7V_Eaw1K6wS5z_5eLeIkcMEoeJUn37whx-R8tag9nc."
                "&v_f=2&gsid={g}"
                "&lang=zh_CN&skin=default&type=0&oldwm=14010_0013&sflag=1&story_ids=").format(s=s, g=gsid)

        if not story_id.endswith('_0'):
            story_id += '_0'

        result = {}
        result['status'] = 1
        result['data'] = {}
        result['msg'] = ''

        urlstory = url2 + story_id

        try:
            res = self.ws.request('GET', urlstory)
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
            res = self.ws.request('POST', url, data=data.encode('utf-8'), headers=head)
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



    def getDataInfo(self):
        url = ( "https://api.weibo.cn/2/page?networktype=wifi&sourcetype=page&c=android&i=8477407&s={s}"
                "&ft=0&wm=14010_0013&aid=01AmyEY7V_Eaw1K6wS5z_5eLeIkcMEoeJUn37whx-R8tag9nc.&v_f=2"
                "&gsid={g}"
                "&lang=zh_CN&page=1&skin=default&count=20&oldwm=14010_0013&sflag=1"
                "&containerid={c}").format(s=s, g=gsid, c=containerid)

        data = {}
        data['state'] = -1
        try:
            res = self.ws.request('GET', url)
            j = res.json()
        except Exception as e:
            logging.exception(e)
            return None

        if 'errno' in j and j['errno'] < 0:
            return j #['errmsg']

        if 'cards' not in j:
            return None
        cards = j['cards']

        text = ''
        for card in cards:
            if 'card_type_name' in card and card['card_type_name'] == '相关超级话题':
                card_group = card['card_group']
                for group in card_group:
                    if 'desc' in group:
                        text = group['desc']
                break
        
        if text:
            postCnt = text.split('帖子')[0]
            fansCnt = text.split(' ')[-1].split('粉丝')[0]
            data['text'] = text
            data['postCnt'] = int(postCnt)
            data['fansCnt'] = int(fansCnt)
            data['date'] = str(datetime.date(datetime.now()))
            data['state'] = 1

        return data


    def checkIn(self):
        url = ('http://mapi.weibo.com/2/page/button?request_url=http%3A%2F%2Fi.huati.weibo.com%2Fmobile%2Fsuper%2Factive_checkin%3F'
                'pageid%3D{id}&networktype=wifi&c=android&i=8477407&s={s}&ft=0'
                '&wm=14010_0013&aid=01AmyEY7V_Eaw1K6wS5z_5eLeIkcMEoeJUn37whx-R8tag9nc.&v_f=2&v_p=54'
                '&gsid={g}'
                '&lang=zh_CN&skin=default&oldwm=14010_0013&sflag=1').format(s=s, g=gsid, id=chid)


        data = {}
        data['status'] = 0
        try:
            res = self.ws.request('GET', url)
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
    r = w.getStory2()
    # r = w.getStory2('xxx')
    print(r)
    # comment = '测试评论'
    # segment_id = '4184181225059656'
    # story_id = '3053424305_0'
    # r = w.postStoryComment(comment, segment_id, story_id)
    # print(r)
    os.system('pause')
