import time
import re
from typing import Tuple, List

from .timeline import Timeline, TimelineItem
from .video import VideoPartInfo
from .tokenizer import getContentJson
from .note_object import NoteObject

class TimelineConverter:
    @staticmethod
    def getTitleJson(title: str, background="#fff359", small=False) -> NoteObject:
        obj = []
        obj.append({ "insert": "\n" })
        size = "17px" if small else "18px"
        if background:
            ex_space = int((16 - len(title)) / 2)
            for _ in range(ex_space):
                title = "　" + title + "　"
            obj.append({
                "attributes": {
                    "size": size,
                    "background": background,
                    "bold": True,
                    "align": "center"
                },
                "insert": title
            })
        else:
            obj.append({
                "attributes": {
                    "size": size,
                    "bold": True,
                    "align": "center"
                },
                "insert": title
            })
        obj.append({
            "attributes": {
                "align": "center"
            },
            "insert": "\n"
        })
        return NoteObject(obj, len(title) + 10)

    @staticmethod
    def getMultiTitleJson(title: str, title2: str, background="#fff359", background2="#fff359") -> NoteObject:
        obj = []
        obj.append({ "insert": "\n" })

        ex_space = int((15 - len(title) - len(title2)) / 4)
        for _ in range(ex_space):
            title = "　" + title + "　"
        for _ in range(ex_space):
            title2 = "　" + title2 + "　"
        size = "18px"
        obj.append({
            "attributes": {
                "size": size,
                "background": background,
                "bold": True,
                "align": "center"
            },
            "insert": title
        })
        obj.append({
            "attributes": {
                "size": size,
                "bold": True,
                "align": "center"
            },
            "insert": " / "
        })
        obj.append({
            "attributes": {
                "size": size,
                "background": background2,
                "bold": True,
                "align": "center"
            },
            "insert": title2
        })
        obj.append({
            "attributes": {
                "align": "center"
            },
            "insert": "\n"
        })
        return NoteObject(obj, len(title) + 10)

    @staticmethod
    async def getTimelineItemJson(item: TimelineItem) -> NoteObject:
        tagContent = item.tag
        if tagContent.startswith('##'):
            return TimelineConverter.getTitleJson(tagContent[2:], background=None, small=True)
        return await getContentJson(tagContent)

    @staticmethod
    def loadTimelineFromCSV(path: str) -> Timeline:
        # before error:UnicodeDecodeError: 'gbk' codec can't decode byte 0x80 in position 4: illegal multibyte sequence
        with open(path, "r", encoding="utf-8-sig") as f:
            csv_l = f.readlines()
        its = [c.replace("\n", "").split(",") for c in csv_l]
        items = [TimelineItem(int(it[0]), it[1], mask=(it[2] if len(it)>=3 else '')) for it in its]
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
                tag = li_re[1].replace(',', '，')
                item = TimelineItem(sec=sec, tag=tag)
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
                    f.write(f"{item.sec},{item.tag}\n")
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
                    tag = item.tag
                    if tag.startswith('##'):
                        continue
                    if tag.endswith('**'):
                        tag = tag[:-2]
                        tag = '🌟 '+tag
                    elif tag.endswith('*'):
                        tag = tag[:-1]
                        tag = '🌟 '+tag
                    elif tag.startswith('🎤'):
                        if not tag.startswith('🎤 '):
                            tag = '🎤 ' + tag[1:]
                    elif tag.startswith('💃'):
                        if not tag.startswith('💃 '):
                            tag = '💃 ' + tag[1:]
                    else:
                        tag = '➖ '+tag
                    # 保存为毫秒
                    f.write(f"{idx}={item.sec * 1000}*{tag}*\n")
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
