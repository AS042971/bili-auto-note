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
from .runtime_timeline import RuntimeTimeline
from .note_object import NoteObject
from .tokenizer import getContentJson, getTitleJson

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
            timeline: Timeline, template: List[str], agent: BilibiliAgent,
            config: PubTimelineConfig,
            confirmed: bool = False,
            previousPartCollection: List[str] = None
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
        runtime_timeline = await RuntimeTimeline.getRuntimeTimeline(timeline, config)

        op_obj = NoteObject()
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
                print(f'{video_part.title} 不归属于任何token，请确认配置')
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

            if offset <= 0 and token_info[video_part_token].first_part and config.tokens[video_part_token].jump_op_desc:
                token_info[video_part_token].first_part = False
                if config.hide_part:
                    op_obj.append({
                        "insert": {
                            "tag": {
                                "cid": video_part.cid,
                                "oid_type": 2,
                                "status": 0,
                                "index": video_part.index,
                                "seconds": -offset,
                                "cidCount": 1,
                                "key": str(round(time.time()*1000)),
                                "desc": config.tokens[video_part_token].jump_op_desc,
                                "title": "",
                                "epid": 0
                            }
                        }
                    }, 1)
                else:
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
                    }, 1)

            # 从原始时间轴中切出分p时间轴
            runtime_timeline.registerPartInfo(video_part, offset, video_part_token, config.tokens[video_part_token].marker, config.hide_part)

        # 合成
        final_submit_obj = NoteObject()

        for line in template:
            if line.endswith('\n'):
                line = line[:-1]
            if line == '.. jump_op':
                final_submit_obj += op_obj
                final_submit_obj.appendNewLine()
            elif line == '.. song_dance':
                song_dance_timeline = runtime_timeline.songAndDance()
                if song_dance_timeline.items:
                    song_dance_obj = NoteObject()
                    song_dance_obj += await getContentJson(config.song_dance_title)
                    for item in song_dance_timeline.items:
                        song_dance_obj += item.getObject()
                    final_submit_obj += song_dance_obj
                    final_submit_obj.appendNewLine()
            elif line == '.. body':
                main_obj = NoteObject()
                last_titles = []
                for item in runtime_timeline:
                    if item.part_names != last_titles:
                        merged_titles = ' / '.join(item.part_names)
                        last_titles = item.part_names
                        main_obj += await getTitleJson(merged_titles, config)
                    main_obj += item.getObject()
                final_submit_obj += main_obj
                final_submit_obj.appendNewLine()
            else:
                line_obj = await getContentJson(line)
                final_submit_obj += line_obj

        # 补全字数
        if final_submit_obj.length < 300:
            sample = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
            ran_str_list = []
            for i in range(300 - final_submit_obj.length):
                char = random.choice(sample)
                ran_str_list.append(char)
            ran_str = ''.join(ran_str_list)

            for _ in range(10):
                final_submit_obj.appendNewLine()
            final_submit_obj.append({
                "attributes": { "color": "#ffffff" },
                "insert": ran_str
            }, len(ran_str))
            final_submit_obj.length = 311

        submit_obj_str = json.dumps(final_submit_obj.obj, indent=None, ensure_ascii=False, separators=(',', ':'))
        data = {
            "oid": video_info.aid,
            "note_id": note_id,
            "title": video_info.title,
            "summary": config.cover,
            "content": submit_obj_str,
            "csrf": agent.csrf,
            "cont_len": max(final_submit_obj.length, 301),
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
