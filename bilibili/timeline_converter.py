import time
import re
from typing import Tuple, List

from .timeline import Timeline, TimelineItem
from .video import VideoPartInfo

class TimelineConverter:
    @staticmethod
    def getTitleJson(title: str) -> Tuple[list, int]:
        obj = []
        obj.append({ "insert": "\n" })
        obj.append({
            "attributes": {
                "size": "18px",
                "background": "#fff359",
                "bold": True,
                "align": "center"
            },
            "insert": "　　　　" + title + "　　　　"
        })
        obj.append({
            "attributes": {
                "align": "center"
            },
            "insert": "\n"
        })
        return (obj, len(title) + 10)

    @staticmethod
    def getTimelineItemJson(item: TimelineItem, info: VideoPartInfo) -> Tuple[list, int]:
        """生成符合Bilibili笔记需求的时间轴条目json对象

        Args:
            item (TimelineItem): 时间轴条目
            info (VideoPartInfo): 视频信息

        Returns:
                list: 对应的json对象
        """
        # 轴内容
        tagContent = item.tag
        if tagContent.startswith('##'):
            return TimelineConverter.getTitleJson(tagContent[2:])
        else:
            obj = []
            # 时间胶囊
            obj.append({
                "insert": {
                    "tag": {
                        "cid": info.cid,
                        "oid_type": 1,
                        "status": 0,
                        "index": info.index,
                        "seconds": item.sec,
                        "cidCount": info.cidCount,
                        "key": str(round(time.time()*1000)),
                        "title": "P" + str(info.index),
                        "epid": 0
                    }
                }
            })
            obj.append({ "insert": "\n" })
            # 轴引导线
            obj.append({
                "attributes": { "color": "#cccccc" },
                "insert": "  └─ "
            })
            if tagContent.startswith('🎶'):
                # 去除歌舞标识
                tagContent = tagContent[1:]
            if item.highlight:
                obj.append({
                    "attributes": {
                        "color": "#ee230d",
                        "bold": True
                    },
                    "insert": tagContent
                })
            else:
                obj.append({
                    "insert": tagContent
                })
            obj.append({ "insert": "\n" })
            return (obj, len(tagContent) + 8)

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
        content_len = 0
        # 内容
        for item in timeline.items:
            (item_obj, item_len) = TimelineConverter.getTimelineItemJson(item, info)
            obj.extend(item_obj)
            content_len += item_len
        content_len += 1
        return (obj, content_len)

    @staticmethod
    def getSeparateTimelineJson(timeline: Timeline, info: VideoPartInfo) -> List[List]:
        """生成分条目的时间戳

        Args:
            timeline (Timeline): 时间轴
            info (VideoPartInfo): 视频信息

        Returns:
            List[List[str, list, int]]: _description_
        """
        results = []
        for item in timeline.items:
            (item_obj, item_len) = TimelineConverter.getTimelineItemJson(item, info)
            results.append([item.tag, item_obj, item_len])
        return results

    @staticmethod
    def loadTimelineFromCSV(path: str) -> Timeline:
        # before error:UnicodeDecodeError: 'gbk' codec can't decode byte 0x80 in position 4: illegal multibyte sequence
        with open(path, "r", encoding="utf-8-sig") as f:
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
    def loadTimelineFromText(path: str) -> Timeline:
        """
        固定格式的txt文件转换为时间轴数据类型并返回
        :param path: txt文件路径
        :return: Timeline
        """
        with open(path, "r", encoding="utf-8") as f:
            lines = [l.replace("\n", "") for l in f.readlines()]
        items = []
        for li in lines:
            try:
                li_re = re.findall("(.+?\d+:\d+) (.+)", li.strip())[0]
                time = li_re[0].split(":")
                x = 1
                sec = 0
                for t in reversed(time):
                    sec += int(t) * x
                    x *= 60
                if li_re[1][-1] == "*":
                    tag = li_re[1][:-1].replace(',', '，')
                    highlight = True
                else:
                    tag = li_re[1].replace(',', '，')
                    highlight = False
                item = TimelineItem(sec=sec, tag=tag, highlight=highlight)
                items.append(item)
            except Exception as e:
                print(e)
                print(f"Please check (file: '{path}' line{lines.index(li)}:'{li}'),continue...")
                continue
        return Timeline(items)

    @staticmethod
    def saveTimelineToCSV(path: str, timeline: Timeline) -> bool:
        """
        时间轴Timeline数据保存为csv文件
        :param path: csv保存路径
        :param items: Timeline
        :return: bool
        """
        try:
            # "utf-8-sig"的原因：能在excel中正确显示
            with open(path, "w", encoding="utf-8-sig") as f:
                for item in timeline:
                    # 保存为秒
                    if not item.tag.startswith('##'):
                        f.write(f"{item.sec},{item.tag},{int(item.highlight)}\n")
        except Exception as e:
            print(e)
            return False
        return True

    @staticmethod
    def saveTimelineToPBF(path: str, timeline: Timeline) -> bool:
        """
        时间轴Timeline数据保存为pbf文件
        :param path: pbf保存路径
        :param items: Timeline
        :return: bool
        """
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("[Bookmark]\n")
                for idx, item in enumerate(timeline):
                    # 保存为毫秒
                    if not item.tag.startswith('##'):
                        f.write(f"{idx}={item.sec * 1000}*{item.tag}*\n")
        except Exception as e:
            print(e)
            return False
        return True

    @staticmethod
    def saveTimelineToText(path: str, timeline: Timeline) -> bool:
        """
        时间轴Timeline数据保存为txt文件
        :param path: txt保存路径
        :param items: Timeline
        :return: bool
        """
        try:
            # "utf-8-sig"的原因：能在excel中正确显示
            with open(path, "w", encoding="utf-8") as f:
                f.write(str(timeline) + '\n')
        except Exception as e:
            print(e)
            return False
        return True
