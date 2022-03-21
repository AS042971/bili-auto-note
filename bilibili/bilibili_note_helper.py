import time
import json
import csv
from urllib.parse import urlencode

from typing import Tuple, List

from .timeline import Timeline, TimelineItem
from .video import VideoInfo, VideoPartInfo
from .agent import BilibiliAgent


class BilibiliNoteHelper:
    @staticmethod
    def getTimelineItemJson(item: TimelineItem, info: VideoPartInfo) -> Tuple[list, int]:
        """生成符合Bilibili笔记需求的时间轴条目json对象

    Args:
        item (TimelineItem): 时间轴条目
        info (VideoPartInfo): 视频信息

    Returns:
        list: 对应的json对象
    """
        obj = []
        # 时间胶囊
        obj.append({"insert": {
            "tag": {"cid": info.cid, "oid_type": 1, "status": 0, "index": info.index, "seconds": item.sec,
                    "cidCount": 1, "key": str(round(time.time() * 1000)), "title": "P" + str(info.index), "epid": 0}}})
        obj.append({"insert": "\n"})
        # 轴引导线
        obj.append({"attributes": {"color": "#cccccc"}, "insert": "  └─ "})
        # 轴内容
        if item.highlight:
            obj.append({"attributes": {"color": "#ee230d", "bold": True}, "insert": item.tag})
        else:
            obj.append({"insert": item.tag})
        obj.append({"insert": "\n"})
        return (obj, len(item.tag) + 8)

    @staticmethod
    def getTimelineJson(timeline: Timeline, info: VideoPartInfo) -> Tuple[list, int]:
        """生成符合Bilibili笔记需求的时间轴json对象

    Args:
        timeline (Timeline): 时间轴
        info (VideoPartInfo): 视频信息

    Returns:
        list: 对应的json对象
    """
        obj = []
        # 标题
        obj.append({"attributes": {"size": "18px", "background": "#fff359", "bold": True, "align": "center"},
                    "insert": "　　　　" + info.title + "　　　　"})
        obj.append({"attributes": {"align": "center"}, "insert": "\n"})
        content_len = len(info.title) + 9
        # 内容
        for item in timeline.items:
            (item_obj, item_len) = BilibiliNoteHelper.getTimelineItemJson(item, info)
            obj.extend(item_obj)
            content_len += item_len
        obj.append({"insert": "\n"})
        content_len += 1
        return (obj, content_len)

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
    def loadTimeline(path: str) -> Timeline:
        # before error:UnicodeDecodeError: 'gbk' codec can't decode byte 0x80 in position 4: illegal multibyte sequence
        with open(path, "r", encoding="utf-8") as f:
            csv_l = f.readlines()
        its = [c.replace("\n", "").split(",") for c in csv_l]
        for i in range(len(its)):
            if len(its[i]) >= 3 and its[i][2] == '1':
                its[i][2] = True
            else:
                its[i][2] = False
        items = [TimelineItem(int(it[0]), it[1], bool(it[2])) for it in its]
        return Timeline(items)

    @staticmethod
    async def sendNote(timeline: Timeline, agent: BilibiliAgent, bvid: str, offsets: List[int], cover: str,
                       publish: bool) -> None:
        """发送笔记

    Args:
        timeline (Timeline): 参考时间轴
        agent (BilibiliAgent): 用于发送的账号
        bvid (str): 目标视频BV号
        offsets (list[int]): 每个分P的开场偏移
        cover (str): 发送到评论区的字符串
        publish (bool): 是否直接发布
    """
        # 获取视频信息
        video_info_res = await agent.get("https://api.bilibili.com/x/web-interface/view", params={"bvid": bvid})
        video_info = BilibiliNoteHelper.getVideoInfo(video_info_res)

        # 获取笔记状态
        note_res = await agent.get("https://api.bilibili.com/x/note/list/archive", params={"oid": video_info.aid})
        note_id = ''
        if not note_res['noteIds']:
            # 没有笔记，插入一个新的空笔记以获取ID
            note_add_res = await agent.post("https://api.bilibili.com/x/note/add",
                                            data={"oid": video_info.aid, "csrf": agent.csrf, "title": video_info.title,
                                                  "summary": " "})
            note_id = note_add_res['note_id']
        else:
            note_id = note_res['noteIds'][0]

        # 发布笔记
        # 检查偏移量和分P数是否一致
        if len(offsets) != len(video_info.parts):
            print(f'偏移量{offsets}数量和视频分段数量({len(video_info.parts)})不一致！')
            if len(offsets) < len(video_info.parts):
                offsets = offsets + ['auto'] * (len(video_info.parts)) - len(offsets)

        current_timestamp = 0
        submit_obj = []
        submit_len = 0
        for video_part_index in range(0, len(video_info.parts)):
            # 遍历每个分P进行计算
            video_part = video_info.parts[video_part_index]
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

            (timeline_obj, timeline_len) = BilibiliNoteHelper.getTimelineJson(part_timeline, video_part)
            submit_obj.extend(timeline_obj)
            submit_len += timeline_len

        submit_obj_str = json.dumps(submit_obj, indent=None, ensure_ascii=False, separators=(',', ':'))
        data = {"oid": video_info.aid, "note_id": note_id, "title": video_info.title, "summary": cover,
                "content": submit_obj_str, "csrf": agent.csrf, "cont_len": submit_len,
                "hash": str(round(time.time() * 1000)), "publish": 1 if publish else 0,
                "auto_comment": 1 if publish else 0}
        submit_res = await agent.post("https://api.bilibili.com/x/note/add", data=data)
        print(submit_res)
