import os
import time
import json
import csv
import asyncio
import random

from typing import Tuple, List

from .timeline import Timeline, TimelineItem
from .video import VideoInfo, VideoPartInfo
from .agent import BilibiliAgent
from .timeline_converter import TimelineConverter
from .pub_timeline_config import PubTimelineConfig

class TokenInfo:
    def __init__(self) -> None:
        self.current_timestamp = 0
        self.video_part_index = 0
        self.first_part = True

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
            config: PubTimelineConfig,
            confirmed: bool = False,
            previousPartCollection: List[str] = []
        ) -> List[str]:
        """发送笔记

        Args:
            timeline (Timeline): 参考时间轴
            agent (BilibiliAgent): 用于发送的账号
            config (PubTimelineConfig): 其他配置信息
            confirmed (bool): 发布前是否不用二次确认, 默认为False
            previousPartCollection (list[int]): 前一次发布的视频分P信息, 默认为空
        Returns:
            List[str]: 如果发布成功，返回新的视频分P信息
        """
        # 获取视频信息
        video_info_res = await agent.get(
            "https://api.bilibili.com/x/web-interface/view",
            params={
                "bvid": config.bvid
            })
        if config.custom_video_info:
            with open(config.custom_video_info, 'r', encoding='utf8') as fp:
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
            print('  配置: '+('笔记会自动发布' if config.publish else '笔记不会自动发布, 请在脚本执行完毕后进入视频笔记区手动发布'))
            if config.publish:
                print(f'  自动发布的评论内容: \n{config.cover}')
            for i in range(min(3, len(timeline.items))):
                print(f'笔记的第{i+1}行：{timeline.items[i].tag}')

        if not confirmed:
            command = input('请确认以上信息准确。是否执行？[y/n]')
            if command != 'Y' and command != 'y':
                return []

        # 开始生成笔记
        token_info = [TokenInfo() for _ in range(len(config.tokens))]

        op_obj = []
        op_len = 0

        main_obj = []
        main_len = 0
        main_collection = []

        song_dance_obj = []
        song_dance_len = 0
        song_dance_collection = []

        # 生成歌舞导航容器
        if config.song_and_dance:
            (_, song_dance_title_obj, song_dance_title_len) = TimelineConverter.getTitleJson('本场歌舞快速导航', background="#ffa0d0")
            song_dance_obj.extend(song_dance_title_obj)
            song_dance_len += song_dance_title_len

        # 生成每个分P的轴
        for video_part in video_info.parts:
            # 自动忽略过短的视频（一般是用来垫的视频，不会对应到offsets序列）
            if video_part.duration < config.ignore_threshold:
                continue

            # 检查这个视频归属于哪个token
            video_part_token = -1
            for i, token in enumerate(config.tokens):
                if not token.key or token.key in video_part.title:
                    video_part_token = i
                    break
            if video_part_token == -1:
                print(f'{video_part.title}不归属于任何token，请确认配置')
                continue

            # 读取分p对应的偏移量信息
            offset = 0
            if len(config.tokens[video_part_token].offsets) == 0 or token_info[video_part_token].video_part_index >= len(config.tokens[video_part_token].offsets):
                raw_offset = 'auto'
            else:
                raw_offset = config.tokens[video_part_token].offsets[token_info[video_part_token].video_part_index]
            token_info[video_part_token].video_part_index += 1
            if isinstance(raw_offset, int):
                offset = raw_offset
                token_info[video_part_token].current_timestamp = offset + video_part.duration
            elif raw_offset == 'auto':
                offset = token_info[video_part_token].current_timestamp
                token_info[video_part_token].current_timestamp = offset + video_part.duration
            else:
                continue

            if config.jumpOP and token_info[video_part_token].first_part and config.tokens[video_part_token].jump_op_desc:
                token_info[video_part_token].first_part = False
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
                            "desc": config.tokens[video_part_token].jump_op_desc,
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
                print(f'分P{video_part.title}不具有任何时间轴条目')
                continue

            if len(part_timeline.items) != 0:
                custom_title = config.tokens[video_part_token].marker
                part_result = await TimelineConverter.getSeparateTimelineJson(part_timeline, video_part, customTitle=custom_title, token=str(video_part_token))
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
            if config.song_and_dance:
                song_dance_timeline = part_timeline.songAndDance()
                if len(song_dance_timeline.items) != 0:
                    custom_title = config.tokens[video_part_token].marker
                    part_result = await TimelineConverter.getSeparateTimelineJson(song_dance_timeline, video_part, customTitle=custom_title, token=str(video_part_token))
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

        if not main_collection:
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
        if config.preface:
            final_submit_obj.append({
                "insert": config.preface
            })
            final_submit_obj.append({ "insert": "\n" })
            final_submit_len += len(config.preface) + 1

        if config.img_cover:
            # 插入封面图
            final_submit_obj.append({
                "insert": {
                    "imageUpload": {
                        "url": config.img_cover,
                        "status": "done",
                        "width": 315,
                        "id": "IMAGE_" + str(round(time.time()*1000)),
                        "source": "video"
                    }
                }
            })
            final_submit_obj.append({ "insert": "\n" })

        # 插入歌舞导航
        if config.song_and_dance and song_dance_collection:
            for item in song_dance_collection:
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
                    merged_titles = ' / '.join(item[4])
                    (_, title_obj, title_len) = TimelineConverter.getTitleJson(merged_titles, '#73fdea')
                    main_obj.extend(title_obj)
                    main_len += title_len

                if item[1]:
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

        if config.img_footer:
            (_, footer_title_obj, footer_title_len) = TimelineConverter.getTitleJson('附图', background="#f8ba00")
            final_submit_obj.extend(footer_title_obj)
            final_submit_len += footer_title_len
            for imgFooterItem in config.img_footer:
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
            "summary": config.cover,
            "content": submit_obj_str,
            "csrf": agent.csrf,
            "cont_len": max(final_submit_len, 301),
            "hash": str(round(time.time()*1000)),
            "publish": 1 if config.publish else 0,
            "auto_comment": 1 if (config.publish and config.auto_comment) else 0,
            "comment_format": 2
        }
        await asyncio.sleep(1)
        submit_res = await agent.post("https://api.bilibili.com/x/note/add", data=data)
        if submit_res['note_id']:
            print(f'执行成功，笔记ID为：{submit_res}')
            return part_collection
        else:
            print(f'执行失败，返回值为{submit_res}')
            return []
