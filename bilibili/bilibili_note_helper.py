import os
import time
import json
import csv
import asyncio
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
    async def sendNote(timeline: Timeline, agent: BilibiliAgent, bvid: str, offsets: List[int], cover: str, publish: bool, confirmed: bool = False, previousPartCollection: List[str] = []) -> List[str]:
        """发送笔记

        Args:
            timeline (Timeline): 参考时间轴
            agent (BilibiliAgent): 用于发送的账号
            bvid (str): 目标视频BV号
            offsets (list[int]): 每个分P的开场偏移
            cover (str): 发送到评论区的字符串
            publish (bool): 是否直接发布
            confirmed (bool): 发布前是否不用二次确认
        """
        # 获取视频信息
        video_info_res = await agent.get(
            "https://api.bilibili.com/x/web-interface/view",
            params={
                "bvid": bvid
            })
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
            print('  配置: '+('笔记会自动发布' if publish else '需要手动发布笔记'))
            if publish:
                print(f'  自动发布的评论内容: \n{cover}')

        if len(offsets) != len(video_info.parts):
            print(f'  注意: 偏移量{offsets}数量和视频分段数量({len(video_info.parts)})不一致！')
            if (len(offsets) < len(video_info.parts)):
                offsets = offsets + ['auto'] * (len(video_info.parts)) - len(offsets)

        if not confirmed:
            command = input('请确认以上信息准确。是否执行？[y/n]')
            if command != 'Y' and command != 'y':
                return []

        current_timestamp = 0
        submit_obj = []
        submit_len = 0

        # 插入每个分P的轴
        for video_part_index in range(0, len(video_info.parts)):
            # 遍历每个分P进行计算
            video_part = video_info.parts[video_part_index]
            # 10分钟以下的视频会被自动忽略
            if video_part.duration < 600:
                continue
            raw_offset = offsets[video_part_index]
            offset = 0
            if isinstance(raw_offset, int):
                offset = raw_offset
                current_timestamp = offset + video_part.duration
            elif raw_offset == 'auto':
                offset = current_timestamp
                current_timestamp = offset + video_part.duration
            else:
                continue

            # 从原始时间轴中切出分p时间轴
            part_timeline = timeline.clip(offset, video_part.duration)
            if len(part_timeline.items) == 0:
                continue

            (timeline_obj, timeline_len) = TimelineConverter.getTimelineJson(part_timeline, video_part)
            submit_obj.extend(timeline_obj)
            submit_len += timeline_len

        submit_obj_str = json.dumps(submit_obj, indent=None, ensure_ascii=False, separators=(',', ':'))
        data = {
            "oid": video_info.aid,
            "note_id": note_id,
            "title": video_info.title,
            "summary": cover,
            "content": submit_obj_str,
            "csrf": agent.csrf,
            "cont_len": submit_len,
            "hash": str(round(time.time()*1000)),
            "publish": 1 if publish else 0,
            "auto_comment": 1 if publish else 0
        }
        await asyncio.sleep(1)
        submit_res = await agent.post("https://api.bilibili.com/x/note/add", data=data)
        if submit_res['note_id']:
            print(f'执行成功，笔记ID为：{submit_res["note_id"]}')
            return part_collection
        else:
            print(f'执行失败，返回值为{submit_res}')
            return []
