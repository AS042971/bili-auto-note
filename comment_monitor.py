#!/usr/bin/python3
import sys
import time
import asyncio
from bilibili import BilibiliNoteHelper, BilibiliAgent
import urllib.parse
import urllib.request


def send_pushplus(data: dict) -> bool:
    """
    :param data: data = {'token': 'pushplus_token(need)', 'title': 'str', 'content': 'content(need)', }
    :return: bool
    """
    data = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url="http://www.pushplus.plus/send", data=data)
    response = urllib.request.urlopen(req, timeout=10)
    print(response.read().decode())


async def main(bvid: str, uname: str):
    # 获取视频信息
    # 这里的所有操作都无需登录
    agent = BilibiliAgent()
    video_info_res = await agent.get("https://api.bilibili.com/x/web-interface/view", params={"bvid": bvid})
    video_info = BilibiliNoteHelper.getVideoInfo(video_info_res)

    print(f'开始监视 {video_info.title} 的评论区...')
    wait_cnt = 0
    shown_ids = []

    while True:
        content = ""
        if wait_cnt % 2 == 0:
            comment_res = await agent.get("https://api.bilibili.com/x/v2/reply/main",
                                          params={"type": 1, "oid": video_info.aid,  # 2是最新评论，3是热门评论
                                                  "mode": 2})
        else:
            comment_res = await agent.get("https://api.bilibili.com/x/v2/reply/main",
                                          params={"type": 1, "oid": video_info.aid,  # 2是最新评论，3是热门评论
                                                  "mode": 3})
        all_replies = comment_res['replies']
        for reply in all_replies:
            reply_uname = reply['member']['uname']
            if reply_uname == uname and reply['rpid'] not in shown_ids:
                pub_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(reply["ctime"]))
                print('==============================')
                print(f'已捕获到 {uname} 的评论：')
                print(reply['content']['message'])
                content += f"已捕获到 {uname} 的评论：\n{reply['content']['message']}\n"
                content += f"发布时间{pub_time}\nAPP直达链接：\n{base_url}{reply['rpid']}\n\n"
                print('==============================')
                shown_ids.append(reply['rpid'])
            if reply['replies']:
                for sub_reply in reply['replies']:
                    sub_reply_uname = sub_reply['member']['uname']
                    if sub_reply_uname == uname and sub_reply['rpid'] not in shown_ids:
                        print('------------------------------')
                        print(f'已捕获到 {uname} 的楼中楼回复：')
                        print(sub_reply['content']['message'])
                        content += f"已捕获到 {uname} 的楼中楼回复：\n{sub_reply['content']['message']}\n"
                        content += f"发布时间{pub_time}\nAPP直达链接：\n{base_url}{sub_reply['rpid']}\n\n"
                        print('------------------------------')
                        shown_ids.append(sub_reply['rpid'])
        if bool(pushplus_token) & bool(content):
            print("尝试请求pushplus服务推送捕获信息...")
            data = {'token': pushplus_token, 'title': f'{uname}评论监控', 'content': content+"持续监控中...", }
            try:
                send_pushplus(data=data)
            except Exception as e:
                print("推送失败，网络错误")
                print(e)
        print('*', end='', flush=True)
        for _ in range(24):
            await asyncio.sleep(5)
            print('*', end='', flush=True)
        wait_cnt += 1
        print(f' 已持续监控 {wait_cnt * 2} 分钟...')


if __name__ == '__main__':
    if len(sys.argv) <= 2:
        print(
            'Usage: comment_monitor.py <BVID> <User name> <pushplus_token from https://www.pushplus.plus/>\n第三项参数为推送服务，非必需填写')
        sys.exit(-1)
    bvid = sys.argv[1]
    uname = sys.argv[2]
    if len(sys.argv) == 4:
        pushplus_token = sys.argv[3]
    else:
        # 推送服务 https://www.pushplus.plus/
        pushplus_token = ""
    base_url = f"https://www.bilibili.com/video/{bvid}?comment_on=1&comment_root_id="
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main(bvid, uname))
