import os
import time
import json
import csv
import asyncio
import random
from urllib.parse import urlencode

from typing import Tuple, List

from .timeline import Timeline, TimelineItem
from .video import VideoInfo, VideoPartInfo
from .agent import BilibiliAgent
from .timeline_converter import TimelineConverter

class BilibiliNoteHelper:
    @staticmethod
    def getVideoPartInfo(cidCount: int, payload: dict) -> VideoPartInfo:
        """从返回的json生成视频分P信息

        Args:
            cidCount (int): 总分P数量
            payload (dict): 分P的json

        Returns:
            VideoPartInfo: 生成的视频分P信息
        """
        cid = payload['cid']
        index = payload['page']
        title = payload['part']
        duration = payload['duration']
        return VideoPartInfo(cid, index, cidCount, title, duration)

    @staticmethod
    def getVideoInfo(payload: dict) -> VideoInfo:
        """生成视频信息

        Args:
            payload (dict): 视频的json

        Returns:
            VideoInfo: 生成的视频信息
        """
        aid = payload['aid']
        pic = payload['pic']
        title = payload['title']
        cnt = len(payload['pages'])
        parts = [BilibiliNoteHelper.getVideoPartInfo(cnt, part_payload) for part_payload in payload['pages']]
        return VideoInfo(aid, pic, title, parts)

    @staticmethod
    async def sendNote(
            timeline: Timeline, agent: BilibiliAgent,
            bvid: str, offsets: List[int],
            cover: str, publish: bool,
            confirmed: bool = False,
            previousPartCollection: List[str] = [],
            ignoreThreshold: int = 600,
            danmakuOffsets: List[int] = [],
            autoComment: bool = True,
            output: str = '',
            songAndDance = True,
            preface = '',
            prefaceNone = '',
            poem = '',
            jumpOP = False,
            imgNone = '',
            imgCover = '',
            imgFooter: List[str] = [],
            customVideoInfo = ''
        ) -> List[str]:
        """发送笔记

        Args:
            timeline (Timeline): 参考时间轴
            agent (BilibiliAgent): 用于发送的账号
            bvid (str): 目标视频BV号
            offsets (list[int]): 每个分P的开场偏移
            cover (str): 发送到评论区的字符串
            publish (bool): 是否直接发布
            confirmed (bool): 发布前是否不用二次确认, 默认为False
            previousPartCollection (list[int]): 前一次发布的视频分P信息, 默认为空
            ignoreThreshold (int): 时间短于此值的分P将被忽略（秒）, 默认为10分钟
            danmakuOffsets(list[int]): 弹幕版每个分P的开场偏移
            output(str): 输出文本轴路径

        Returns:
            List[str]: 如果发布成功，返回新的视频分P信息
        """
        # 获取视频信息
        video_info_res = await agent.get(
            "https://api.bilibili.com/x/web-interface/view",
            params={
                "bvid": bvid
            })
        if customVideoInfo:
            with open(customVideoInfo, 'r', encoding='utf8') as fp:
                json_data = json.load(fp)
                if json_data:
                    video_info_res['pages'] = json_data

        video_info = BilibiliNoteHelper.getVideoInfo(video_info_res)
        part_collection = [part.cid for part in video_info.parts]
        if previousPartCollection == part_collection:
            # 分P数量没有发生变化
            return part_collection

        await asyncio.sleep(1)
        # 获取笔记状态
        note_res = await agent.get(
            "https://api.bilibili.com/x/note/list/archive",
            params={
                "oid": video_info.aid
            })
        note_id = ''
        if not note_res['noteIds']:
            await asyncio.sleep(1)
            # 没有笔记，插入一个新的空笔记以获取ID
            note_add_res = await agent.post(
                "https://api.bilibili.com/x/note/add",
                data={
                    "oid": video_info.aid,
                    "csrf": agent.csrf,
                    "title": video_info.title,
                    "summary": " "
                })
            note_id = note_add_res['note_id']
        else:
            note_id = note_res['noteIds'][0]

        # 发布笔记
        # 检查偏移量和分P数是否一致
        if not confirmed:
            print('请确认以下信息是否准确（自动监控模式下本提示只会出现一次）')
            print(f'  视频名: {video_info.title}')
            print('  配置: '+('笔记会自动发布' if publish else '笔记不会自动发布, 请在脚本执行完毕后进入视频笔记区手动发布'))
            if publish:
                print(f'  自动发布的评论内容: \n{cover}')
            if output:
                print(f'  更新笔记时文本轴将同步保存于 {output}')

        if len(offsets) + len(danmakuOffsets) != len(video_info.parts):
            print(f'  注意: 偏移量{offsets}, {danmakuOffsets} 总数量和视频分段数量({len(video_info.parts)})不一致！')

        if not confirmed:
            command = input('请确认以上信息准确。是否执行？[y/n]')
            if command != 'Y' and command != 'y':
                return []

        # 开始生成笔记
        current_timestamp = 0
        current_danmaku_timestamp = 0
        video_part_index = 0
        video_part_danmaku_index = 0

        first_part = True
        first_danmaku_part = True

        op_obj = []
        op_len = 0

        main_obj = []
        main_len = 0
        main_collection = []

        song_dance_obj = []
        song_dance_len = 0
        song_dance_collection = []

        txt_timeline = ''

        if songAndDance:
            (_, song_dance_title_obj, song_dance_title_len) = TimelineConverter.getTitleJson('本场歌舞快速导航', background="#ffa0d0")
            song_dance_obj.extend(song_dance_title_obj)
            song_dance_len += song_dance_title_len

        # (_, main_title_obj, main_title_len) = TimelineConverter.getTitleJson('正片', background="#fff359")
        # main_obj.extend(main_title_obj)
        # main_len += main_title_len

        # 插入每个分P的轴
        for video_part in video_info.parts:
            # 自动忽略过短的视频（一般是用来垫的视频，不会对应到offsets序列）
            if video_part.duration < ignoreThreshold:
                continue

            is_video_part_danmaku = '弹幕' in video_part.title and '无弹幕' not in video_part.title

            # 读取分p对应的偏移量信息
            offset = 0
            if not danmakuOffsets:
                # 所有分P统一由offsets管理
                if len(offsets) == 0 or video_part_index >= len(offsets):
                    raw_offset = 'auto'
                else:
                    raw_offset = offsets[video_part_index]
                video_part_index += 1
                if isinstance(raw_offset, int):
                    offset = raw_offset
                    current_timestamp = offset + video_part.duration
                elif raw_offset == 'auto':
                    offset = current_timestamp
                    current_timestamp = offset + video_part.duration
                else:
                    continue
            else:
                # 分P分别由offsets和danmakuOffsets决定
                if is_video_part_danmaku:
                    # 这是一个弹幕视频
                    if video_part_danmaku_index == 0 and ('中' in video_part.title or '下' in video_part.title):
                        video_part_danmaku_index = 1
                        current_danmaku_timestamp = current_timestamp
                        first_danmaku_part = False
                    if len(danmakuOffsets) == 0 or video_part_danmaku_index >= len(danmakuOffsets):
                        raw_offset = 'auto'
                    else:
                        raw_offset = danmakuOffsets[video_part_danmaku_index]
                    video_part_danmaku_index += 1
                    if isinstance(raw_offset, int):
                        offset = raw_offset
                        current_danmaku_timestamp = offset + video_part.duration
                    elif raw_offset == 'auto':
                        offset = current_danmaku_timestamp
                        current_danmaku_timestamp = offset + video_part.duration
                    else:
                        continue
                else:
                    # 这是一个无弹幕视频
                    if video_part_index == 0 and ('中' in video_part.title or '下' in video_part.title):
                        video_part_index = 1
                        current_timestamp = current_danmaku_timestamp
                        first_part = False
                    if len(offsets) == 0 or video_part_index >= len(offsets):
                        raw_offset = 'auto'
                    else:
                        raw_offset = offsets[video_part_index]
                    video_part_index += 1
                    if isinstance(raw_offset, int):
                        offset = raw_offset
                        current_timestamp = offset + video_part.duration
                    elif raw_offset == 'auto':
                        offset = current_timestamp
                        current_timestamp = offset + video_part.duration
                    else:
                        continue

            if jumpOP and not is_video_part_danmaku and first_part:
                first_part = False
                op_obj.append({
                    "insert": {
                        "tag": {
                            "cid": video_part.cid,
                            "oid_type": 0,
                            "status": 0,
                            "index": video_part.index,
                            "seconds": -offset,
                            "cidCount": video_part.cidCount,
                            "key": str(round(time.time()*1000)),
                            "desc": "🪂点此跳过OP (纯净版)",
                            "title": "",
                            "epid": 0
                        }
                    }
                })
                op_obj.append({ "insert": "\n" })
                op_len += 2
            if jumpOP and is_video_part_danmaku and first_danmaku_part:
                first_danmaku_part = False
                op_obj.append({
                    "insert": {
                        "tag": {
                            "cid": video_part.cid,
                            "oid_type": 0,
                            "status": 0,
                            "index": video_part.index,
                            "seconds": -offset,
                            "cidCount": video_part.cidCount,
                            "key": str(round(time.time()*1000)),
                            "desc": "🪂点此跳过OP (弹幕版)",
                            "title": "",
                            "epid": 0
                        }
                    }
                })
                op_obj.append({ "insert": "\n" })
                op_len += 2

            # 从原始时间轴中切出分p时间轴
            part_timeline = timeline.clip(offset, video_part.duration)
            if len(part_timeline.items) == 0:
                continue

            # 将分p时间轴保存到文本文件
            txt_timeline += (video_part.title)
            txt_timeline += '\n'
            txt_timeline += str(part_timeline)
            txt_timeline += '\n\n'

            # 添加分p标题和内容
            # background = "#73fdea" if is_video_part_danmaku else "#fff359"
            # (_, title_obj, title_len) = TimelineConverter.getTitleJson(video_part.title, background=background)
            # main_obj.extend(title_obj)
            # main_len += title_len
            # (timeline_obj, timeline_len) = await TimelineConverter.getTimelineJson(part_timeline, video_part)
            # main_obj.extend(timeline_obj)
            # main_len += timeline_len

            if len(part_timeline.items) != 0:
                custom_title = '弹' if is_video_part_danmaku else ''
                part_result = await TimelineConverter.getSeparateTimelineJson(part_timeline, video_part, customTitle=custom_title)
                if not main_collection:
                    main_collection = part_result
                else:
                    for item in part_result:
                        found = False
                        # 合并同名项目
                        for ref in main_collection:
                            if item[0] == ref[0]:
                                ref[1].extend(item[1])
                                ref[3] += 1
                                ref[4].extend(item[4])
                                found = True
                                break
                        if not found:
                            main_collection.append(item)

            # 筛选分p的歌舞成分
            if songAndDance:
                song_dance_timeline = part_timeline.songAndDance()
                if len(song_dance_timeline.items) != 0:
                    custom_title = '弹' if is_video_part_danmaku else ''
                    part_result = await TimelineConverter.getSeparateTimelineJson(song_dance_timeline, video_part, customTitle=custom_title)
                    if not song_dance_collection:
                        song_dance_collection = part_result
                    else:
                        for item in part_result:
                            found = False
                            # 合并同名项目
                            for ref in song_dance_collection:
                                if item[0] == ref[0]:
                                    ref[1].extend(item[1])
                                    ref[3] += 1
                                    found = True
                                    break
                            if not found:
                                song_dance_collection.append(item)

        # 插入诗歌
        poem_obj = []
        poem_len = 0
        if poem:
            (_, poem_title_obj, poem_title_len) = TimelineConverter.getTitleJson('定场诗', background="#f8ba00")
            poem_obj.extend(poem_title_obj)
            poem_len += poem_title_len
            poem_lines = poem.split('\n')
            for poem_line in poem_lines:
                poem_obj.append({
                    "insert": poem_line
                })
                poem_obj.append({
                    "attributes": {
                        "align": "center"
                    },
                    "insert": '\n'
                })
                poem_len += len(poem_line) + 1

        if not main_collection and not poem_obj:
            print('没有可用的笔记内容')
            return part_collection

        # 合成
        final_submit_obj = []
        final_submit_len = 0

        # 插入OP跳转
        if op_obj:
            final_submit_obj.extend(op_obj)
            final_submit_len += op_len

        # 插入前言
        if main_collection:
            if preface:
                final_submit_obj.append({
                    "insert": preface
                })
                final_submit_obj.append({ "insert": "\n" })
                final_submit_len += len(preface) + 1
        else:
            if prefaceNone:
                final_submit_obj.append({
                    "insert": prefaceNone
                })
                final_submit_obj.append({ "insert": "\n" })
                final_submit_len += len(prefaceNone) + 1
            elif preface:
                final_submit_obj.append({
                    "insert": preface
                })
                final_submit_obj.append({ "insert": "\n" })
                final_submit_len += len(preface) + 1

        if main_collection and imgCover:
            # 插入封面图
            final_submit_obj.append({
                "insert": {
                    "imageUpload": {
                        "url": imgCover,
                        "status": "done",
                        "width": 315,
                        "id": "IMAGE_" + str(round(time.time()*1000)),
                        "source": "video"
                    }
                }
            })
            final_submit_obj.append({ "insert": "\n" })

        # 插入诗歌
        if poem_obj:
            final_submit_obj.extend(poem_obj)
            final_submit_len += poem_len

        # 插入歌舞导航
        if songAndDance and song_dance_collection:
            for item in song_dance_collection:
                # song_dance_obj.append({
                #     "attributes": { "color": "#cccccc" },
                #     "insert": "┌ "
                # })
                for i, o in enumerate(item[1]):
                    song_dance_obj.append(o)
                    if i != len(item[1]) - 1:
                        song_dance_obj.append({
                            "attributes": { "color": "#cccccc" },
                            "insert": " "
                        })
                song_dance_obj.append({
                    "attributes": { "color": "#cccccc" },
                    "insert": " ⇙"
                })
                song_dance_obj.append({
                    "insert": "\n"
                })
                song_dance_obj.extend(item[2])
                song_dance_len += item[3]
            final_submit_obj.extend(song_dance_obj)
            final_submit_len += song_dance_len

        # 插入主轴
        # final_submit_obj.extend(main_obj)
        # final_submit_len += main_len

        if main_collection:
            last_titles = []
            for item in main_collection:
                if item[4] != last_titles:
                    if len(item[4]) == 1:
                        is_video_part_danmaku1 = '弹幕' in item[4][0] and '无弹幕' not in item[4][0]
                        background1 = "#73fdea" if is_video_part_danmaku1 else "#fff359"
                        (_, title_obj, title_len) = TimelineConverter.getTitleJson(item[4][0], background1)
                        main_obj.extend(title_obj)
                        main_len += title_len
                    else:
                        is_video_part_danmaku1 = '弹幕' in item[4][0] and '无弹幕' not in item[4][0]
                        background1 = "#73fdea" if is_video_part_danmaku1 else "#fff359"
                        is_video_part_danmaku2 = '弹幕' in item[4][1] and '无弹幕' not in item[4][1]
                        background2 = "#73fdea" if is_video_part_danmaku2 else "#fff359"

                        (_, title_obj, title_len) = TimelineConverter.getMultiTitleJson(item[4][0], item[4][1], background1, background2)
                        main_obj.extend(title_obj)
                        main_len += title_len

                if item[1][0]:
                    for i, o in enumerate(item[1]):
                        main_obj.append(o)
                        if i != len(item[1]) - 1:
                            main_obj.append({
                                "attributes": { "color": "#cccccc" },
                                "insert": " "
                            })
                    main_obj.append({
                        "attributes": { "color": "#cccccc" },
                        "insert": " ⇙"
                    })
                    main_obj.append({
                        "insert": "\n"
                    })
                main_obj.extend(item[2])
                main_len += item[3]
                last_titles = item[4]
            final_submit_obj.extend(main_obj)
            final_submit_len += main_len

        if imgFooter:
            (_, footer_title_obj, footer_title_len) = TimelineConverter.getTitleJson('附图', background="#f8ba00")
            final_submit_obj.extend(footer_title_obj)
            final_submit_len += footer_title_len
            for imgFooterItem in imgFooter:
                final_submit_obj.append({
                    "insert": {
                        "imageUpload": {
                            "url": imgFooterItem,
                            "status": "done",
                            "width": 315,
                            "id": "IMAGE_" + str(round(time.time()*1000)),
                            "source": "video"
                        }
                    }
                })
                final_submit_obj.append({ "insert": "\n" })

        if output:
            # 将文本轴存储在文件中
            try:
                with open(output, "w", encoding="utf-8") as f:
                    f.write(txt_timeline)
            except Exception as e:
                print('文本轴写入失败，错误原因：')
                print(e)

        if not main_obj and imgNone:
            # 插入羊驼滑跪图
            final_submit_obj.append({
                "insert": {
                        "imageUpload": {
                        "url": imgNone,
                        "status": "done",
                        "width": 315,
                        "id": "IMAGE_" + str(round(time.time()*1000)),
                        "source": "video"
                    }
                }
            })
            final_submit_obj.append({ "insert": "\n" })

        # 补全字数
        if final_submit_len < 300:
            sample = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
            ran_str_list = []
            for i in range(300 - final_submit_len):
                char = random.choice(sample)
                ran_str_list.append(char)
            ran_str = ''.join(ran_str_list)

            for _ in range(10):
                final_submit_obj.append({ "insert": "\n" })
            final_submit_obj.append({
                "attributes": { "color": "#ffffff" },
                "insert": ran_str
            })
            final_submit_len = 311

        submit_obj_str = json.dumps(final_submit_obj, indent=None, ensure_ascii=False, separators=(',', ':'))
        data = {
            "oid": video_info.aid,
            "note_id": note_id,
            "title": video_info.title,
            "summary": cover,
            "content": submit_obj_str,
            "csrf": agent.csrf,
            "cont_len": max(final_submit_len, 301),
            "hash": str(round(time.time()*1000)),
            "publish": 1 if publish else 0,
            "auto_comment": 1 if (publish and autoComment) else 0,
            "comment_format": 2
        }
        await asyncio.sleep(1)
        submit_res = await agent.post("https://api.bilibili.com/x/note/add", data=data)
        if submit_res['note_id']:
            print(f'执行成功，笔记ID为：{submit_res["note_id"]}')
            return part_collection
        else:
            print(f'执行失败，返回值为{submit_res}')
            return []
