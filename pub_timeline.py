#!/usr/bin/python3
from bilibili import BilibiliAgent, Timeline, TimelineItem, BilibiliNoteHelper, TimelineConverter
import asyncio
import sys
import json
import os
import time

async def main(config_path: str):
    with open(config_path,'r',encoding='utf8') as fp:
        json_data = json.load(fp)
        agent = BilibiliAgent(json_data['cookie'])
        bvid = json_data['bvid']
        offsets = json_data['offsets']
        cover = json_data['cover']
        publish = json_data['publish']
        if 'watch' in json_data:
            watch = json_data['watch']
        else:
            watch = False

        if not watch:
            timeline = TimelineConverter.loadTimelineFromCSV(json_data['timeline'])
            await BilibiliNoteHelper.sendNote(timeline, agent, bvid, offsets, cover, publish)
        else:
            print('请注意，自动监控功能已打开，每次目标视频分P变化时将自动更新笔记，直到目标视频数量和设定偏移量数量相同。')
            failed_cnt = 0
            wait_cnt = 0
            published_parts = []
            modify_time = 0
            first_time = True
            # 退出循环条件：失败5次/分P数量和标记数量一致且时间轴2小时内均未更新
            while failed_cnt <= 5 and (len(published_parts) != len(offsets) or modify_time + 7200 > time.time()):
                try:
                    wait_cnt += 1
                    print(f'正在开始第 {wait_cnt} 次任务 ...')
                    new_modify_time = os.path.getmtime(json_data['timeline'])
                    if new_modify_time != modify_time and not first_time:
                        print('检测到轴更新，将强制进行发布')
                        published_parts = []
                        modify_time = new_modify_time
                    timeline = TimelineConverter.loadTimelineFromCSV(json_data['timeline'])
                    if first_time:
                        # 首次，正常地发布笔记，需要进行确认
                        published_parts = await BilibiliNoteHelper.sendNote(timeline, agent, bvid, offsets, cover, publish)
                        first_time = False
                    else:
                        # 后续循环，不进行确认，同时自动发布
                        new_published_parts = await BilibiliNoteHelper.sendNote(timeline, agent, bvid, offsets, cover, publish, True, published_parts)
                        if new_published_parts != published_parts:
                            print('视频列表更新，已自动更新笔记')
                            published_parts = new_published_parts
                        else:
                            print('视频列表无变化')
                    failed_cnt = 0
                    # 等待2分钟
                    for _ in range(24):
                        await asyncio.sleep(5)
                        print('*', end='', flush=True)
                    print('')
                except:
                    failed_cnt += 1
                    print(f'当前共计失败 {failed_cnt} 次')
                    # 等待2分钟
                    for _ in range(24):
                        await asyncio.sleep(5)
                        print('*', end='', flush=True)

            if failed_cnt > 5:
                print('程序因出错退出，请检查日志输出')
            else:
                print('视频分P数量已达到要求，且轴文件已长时间未更新，程序自动退出')
        await agent.close()

if __name__ == '__main__':
    # add default config filepath
    if len(sys.argv) == 1:
        st = "./config/pub_timeline.json"
        print(f'Loading default config file: {st}')
        try:
            with open(st, "r", encoding="utf-8") as f:
                pass
            print(f'Successfully loaded {st}')
        except FileNotFoundError as e_f:
            print(e_f)
            print('Usage: pub_timeline.py <path to config file>')
            sys.exit(-1)
    else:
        st = sys.argv[1]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main(st))
