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
    async def sendNote(
            timeline: Timeline, agent: BilibiliAgent,
            bvid: str, offsets: List[int],
            cover: str, publish: bool,
            confirmed: bool = False,
            previousPartCollection: List[str] = [],
            ignoreThreshold: int = 600,
            danmakuOffsets: List[int] = [],
            autoComment: bool = True,
            output: str = ''
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

        current_timestamp = 0
        current_danmaku_timestamp = 0
        video_part_index = 0
        video_part_danmaku_index = 0

        submit_obj = []
        submit_len = 0

        txt_timeline = ''

        # 插入每个分P的轴
        for video_part in video_info.parts:
            # 自动忽略过短的视频（一般是用来垫的视频，不会对应到offsets序列）
            if video_part.duration < ignoreThreshold:
                continue

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
                if '弹幕' in video_part.title and '无弹幕' not in video_part.title:
                    # 这是一个弹幕视频
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

            # 从原始时间轴中切出分p时间轴
            part_timeline = timeline.clip(offset, video_part.duration)
            if len(part_timeline.items) == 0:
                continue

            txt_timeline += (video_part.title)
            txt_timeline += '\n'
            txt_timeline += str(part_timeline)
            txt_timeline += '\n\n'

            (timeline_obj, timeline_len) = TimelineConverter.getTimelineJson(part_timeline, video_part)
            submit_obj.extend(timeline_obj)
            submit_len += timeline_len

        if not submit_obj:
            print('没有可用的笔记内容')
            return part_collection

        if output:
            # 将文本轴存储在文件中
            try:
                with open(output, "w", encoding="utf-8") as f:
                    f.write(txt_timeline)
            except Exception as e:
                print('文本轴写入失败，错误原因：')
                print(e)

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
            "auto_comment": 1 if (publish and autoComment) else 0
        }
        await asyncio.sleep(1)
        submit_res = await agent.post("https://api.bilibili.com/x/note/add", data=data)
        if submit_res['note_id']:
            print(f'执行成功，笔记ID为：{submit_res["note_id"]}')
            return part_collection
        else:
            print(f'执行失败，返回值为{submit_res}')
            return []
