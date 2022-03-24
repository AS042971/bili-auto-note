import sys
import asyncio
from bilibili import BilibiliNoteHelper, BilibiliAgent

async def main(bvid: str, uname: str):
    # 获取视频信息
    # 这里的所有操作都无需登录
    agent = BilibiliAgent()
    video_info_res = await agent.get(
        "https://api.bilibili.com/x/web-interface/view",
        params={
            "bvid": bvid
        })
    video_info = BilibiliNoteHelper.getVideoInfo(video_info_res)

    print(f'开始监视 {video_info.title} 的评论区...')
    wait_cnt = 0
    last_reply_id = 0
    shown_ids = []

    while True:
        comment_res = await agent.get(
            "https://api.bilibili.com/x/v2/reply/main",
            params={
                "type": 1,
                "oid":video_info.aid,
                # 2是最新评论，3是热门评论
                "mode": 2
        })

        new_reply = comment_res['replies'][0]
        new_reply_id = new_reply['rpid']
        if new_reply_id != last_reply_id:
            # 评论区发生了更新
            for reply in comment_res['replies']:
                if reply['rpid'] == last_reply_id:
                    break
                reply_uname = reply['member']['uname']
                if reply_uname == uname:
                    print('==============================')
                    print(f'已捕获到 {uname} 的评论：')
                    print(reply['content']['message'])
                    print('==============================')
            last_reply_id = new_reply_id
        for i in range(12):
            await asyncio.sleep(5)
            print('*', end='', flush=True)
        wait_cnt += 1
        print(f' 已持续监控 {wait_cnt} 分钟...')

if __name__ == '__main__':
    if len(sys.argv) <= 2:
        print('Usage: comment_monitor.py <BVID> <User name>')
        sys.exit(-1)

    bvid = sys.argv[1]
    uname = sys.argv[2]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main(bvid, uname))
