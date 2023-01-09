#!/usr/bin/python3
from enum import auto
from bilibili import BilibiliAgent, BilibiliNoteHelper, TimelineConverter, PubTimelineConfig
import asyncio
import sys
import json
import os
import time

async def main(config_path: str):
    with open(config_path,'r',encoding='utf8') as fp:
        json_data = json.load(fp)

        # 基础信息
        agent = BilibiliAgent(json_data['cookie'])
        config = PubTimelineConfig(json_data)
        # 读取其他选项
        watch: bool = json_data['watch'] if 'watch' in json_data else False
        confirm: bool = json_data['confirm'] if 'confirm' in json_data else True

        if not watch:
            timeline = TimelineConverter.loadTimelineFromCSV(json_data['timeline'])

            await BilibiliNoteHelper.sendNote(timeline, agent, config, confirmed=not confirm)
        else:
            print('请注意，自动监控功能已打开，每次目标视频分P变化或笔记文件更新时将自动更新笔记')
            failed_cnt = 0
            wait_cnt = 0
            published_parts = []
            modify_time = os.path.getmtime(json_data['timeline'])
            first_time = True
            # 退出循环条件：必须手动退出循环
            while True:
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
                        # 首次，正常地发布笔记
                        published_parts = await BilibiliNoteHelper.sendNote(timeline, agent, config ,confirmed= not confirm)
                        first_time = False
                    else:
                        # 后续循环，不进行确认，同时自动发布
                        new_published_parts = await BilibiliNoteHelper.sendNote(timeline, agent, config, confirmed=True, previousPartCollection=published_parts)
                        if new_published_parts != published_parts:
                            print('已自动更新笔记')
                            published_parts = new_published_parts
                        else:
                            print('视频列表和轴文件均无变化')
                    failed_cnt = 0
                except Exception as e:
                    failed_cnt += 1
                    print(f'当前共计连续失败 {failed_cnt} 次，错误原因如下：')
                    print(e)
                    # 额外等待2分钟
                    for _ in range(24):
                        await asyncio.sleep(5)
                        print('*', end='', flush=True)
                    print('')
                finally:
                    # 等待2分钟
                    for _ in range(24):
                        await asyncio.sleep(5)
                        print('*', end='', flush=True)
                    print(' ', end='', flush=True)
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
