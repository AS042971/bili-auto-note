#!/usr/bin/python3
from bilibili import BilibiliAgent, BilibiliNoteHelper, TimelineConverter
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
        bvid = json_data['bvid']

        # 读取偏移量的信息
        offsets = json_data['offsets']
        if 'danmakuOffsets' in json_data:
            danmaku_offsets = json_data['danmakuOffsets']
        else:
            danmaku_offsets = []

        if 'ignoreThreshold' in json_data:
            ignore_threshold = json_data['ignoreThreshold']
        else:
            ignore_threshold = 600

        # 读取是否发布的信息
        publish = json_data['publish']
        cover = json_data['cover']

        # 读取是否监控的信息
        if 'watch' in json_data:
            watch = json_data['watch']
        else:
            print(f'可更新配置文件 {config_path} 增加"watch"字段，用于自动监控视频分P和笔记文件的变化，可参考example目录中的示例')
            watch = False

        # 读取文本轴存储
        if 'output' in json_data:
            output = json_data['output']
        else:
            output = ''

        # 读取其他选项
        if 'preface' in json_data:
            preface = json_data['preface']
        else:
            preface = ''

        if 'songAndDanceAbstract' in json_data:
            song_and_dance = json_data['songAndDanceAbstract']
        else:
            song_and_dance = True

        if 'prefaceNone' in json_data:
            prefaceNone = json_data['prefaceNone']
        else:
            prefaceNone = ''

        if 'jumpOP' in json_data:
            jumpOP = json_data['jumpOP']
        else:
            jumpOP = False

        if 'poem' in json_data:
            poem_path = json_data['poem']
            with open(poem_path, 'r', encoding='utf8') as file:
                poem = file.read()
        else:
            poem = ''

        if not watch:
            timeline = TimelineConverter.loadTimelineFromCSV(json_data['timeline'])

            await BilibiliNoteHelper.sendNote(timeline, agent, bvid, offsets, cover, publish, danmakuOffsets=danmaku_offsets, ignoreThreshold=ignore_threshold, output=output, preface=preface, songAndDance=song_and_dance, prefaceNone=prefaceNone, jumpOP=jumpOP, poem=poem)
        else:
            print('请注意，自动监控功能已打开，每次目标视频分P变化或笔记文件更新时将自动更新笔记')
            failed_cnt = 0
            wait_cnt = 0
            published_parts = []
            modify_time = os.path.getmtime(json_data['timeline'])
            first_time = True
            # 退出循环条件：连续失败30次（120分钟）或分P数量和标记数量一致且时间轴2小时内均未更新
            while failed_cnt <= 30 and (len(published_parts) != len(offsets) + len(danmaku_offsets) or modify_time + 7200 > time.time()):
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
                        published_parts = await BilibiliNoteHelper.sendNote(timeline, agent, bvid, offsets, cover, publish, danmakuOffsets=danmaku_offsets, ignoreThreshold=ignore_threshold, output=output, preface=preface, songAndDance=song_and_dance, prefaceNone=prefaceNone, jumpOP=jumpOP, poem=poem)
                        first_time = False
                    else:
                        # 后续循环，不进行确认，同时自动发布
                        new_published_parts = await BilibiliNoteHelper.sendNote(timeline, agent, bvid, offsets, cover, publish, confirmed=True, previousPartCollection = published_parts, danmakuOffsets=danmaku_offsets, ignoreThreshold=ignore_threshold, autoComment=False, output=output, preface=preface, songAndDance=song_and_dance, prefaceNone=prefaceNone, jumpOP=jumpOP, poem=poem)
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
            if failed_cnt > 30:
                print('程序因在120分钟内连续多次失败退出，请检查日志输出')
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
