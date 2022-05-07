#!/usr/bin/python3
import sys
import asyncio
from bilibili import BilibiliNoteHelper, BilibiliAgent
import urllib.parse
import urllib.request
import time
import json

def send_pushplus(data: dict) -> bool:
    """
    :param data: data = {'token': 'pushplus_token(need)', 'title': 'str', 'content': 'content(need)', }
    :return: bool
    """
    data = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url="http://www.pushplus.plus/send", data=data)
    response = urllib.request.urlopen(req, timeout=10)
    print(response.read().decode())


async def main(config_path: str):
    with open(config_path,'r',encoding='utf8') as fp:
        json_data = json.load(fp)

        # 基础信息
        agent = BilibiliAgent(json_data['cookie'])
        bvid = json_data['bvid']
        mid = json_data['mid']
        comment = json_data['comment']

        if 'pushplus' in json_data:
            pushplus_token = json_data['pushplus']
        else:
            pushplus_token = ''

        video_info_res = await agent.get(
        "https://api.bilibili.com/x/web-interface/view",
        params={
            "bvid": bvid
        })
        video_info = BilibiliNoteHelper.getVideoInfo(video_info_res)

        print(f'开始监视 {video_info.title} 的笔记发布情况...')
        wait_cnt = 0

        while True:
            article_res = await agent.get(
                "https://api.bilibili.com/x/space/article",
                params={
                    "mid": mid
            })
            all_articles = article_res['articles']
            for article in all_articles:
                if article['cover_avid'] == video_info.aid:
                    print("已监测到新发布的笔记")
                    cvid = article['id']
                    url = f'https://www.bilibili.com/h5/note-app/view?cvid={cvid}&pagefrom=comment'
                    full_comment = f'{url}\n{comment}'
                    await agent.post(
                        'http://api.bilibili.com/x/v2/reply/add',
                        params={
                            "type": 1,
                            "oid": video_info.aid,
                            "csrf": agent.csrf,
                            "message": full_comment
                    })
                    print('已完成评论发布，程序自动退出')
                    if bool(pushplus_token):
                        print("尝试请求pushplus服务推送捕获信息...")
                        data = {'token': pushplus_token, 'title': f'{video_info.title}评论自动发布', 'content': full_comment }
                        try:
                            send_pushplus(data=data)
                        except Exception as e:
                            print("推送失败，网络错误")
                            print(e)
                    sys.exit(0)
            for _ in range(24):
                await asyncio.sleep(5)
                print('*', end='', flush=True)
            wait_cnt += 1
            print(f' 已持续监控 {wait_cnt * 2} 分钟...')

if __name__ == '__main__':
    # add default config filepath
    if len(sys.argv) == 1:
        st = "./config/comment_sender.json"
        print(f'Loading default config file: {st}')
        try:
            with open(st, "r", encoding="utf-8") as f:
                pass
            print(f'Successfully loaded {st}')
        except FileNotFoundError as e_f:
            print(e_f)
            print('Usage: comment_sender.py <path to config file>')
            sys.exit(-1)
    else:
        st = sys.argv[1]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main(st))
