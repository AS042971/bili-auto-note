import time
import re
from typing import Tuple, List

from .timeline import Timeline, TimelineItem
from .video import VideoPartInfo
from .agent import BilibiliAgent

class TimelineConverter:
    @staticmethod
    async def getBvTitle(bvid: str) -> str:
        agent = BilibiliAgent()
        video_info_res = await agent.get(
            "https://api.bilibili.com/x/web-interface/view",
            params={
                "bvid": bvid
        })
        await agent.close()
        return video_info_res['title']

    @staticmethod
    def getTitleJson(title: str, background="#fff359", small=False) -> Tuple[list, int]:
        obj = []
        obj.append({ "insert": "\n" })
        size = "16px" if small else "18px"
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
        return (obj, len(title) + 10)

    @staticmethod
    async def getTimelineItemJson(item: TimelineItem, info: VideoPartInfo, customTitle = '') -> Tuple[list, int]:
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
            return TimelineConverter.getTitleJson(tagContent[2:], background=None, small=True)
        else:
            title = customTitle if customTitle else "P" + str(info.index)
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
                        "title": title,
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
            contentType = ''
            if tagContent.endswith('**'):
                tagContent = tagContent[:-2]
                contentType = 'ex_mark'
            elif tagContent.endswith('*'):
                tagContent = tagContent[:-1]
                contentType = 'mark'
            elif tagContent.startswith('🎤'):
                contentType = 'song'
            elif tagContent.startswith('💃'):
                contentType = 'dance'

            contentParts = re.split('(BV[A-Za-z0-9]{10})',tagContent)
            for part in contentParts:
                if (re.match('(BV[A-Za-z0-9]{10})', part)):
                    title = await TimelineConverter.getBvTitle(part)
                    title = '▶️' + title
                    obj.append({
                        "attributes": {
                            "color": "#0b84ed",
                            "link": "https://www.bilibili.com/video/" + part
                        },
                        "insert": title
                    })
                else:
                    if contentType == 'ex_mark':
                        obj.append({
                            "attributes": {
                                "color": "#ee230d",
                                "bold": True
                            },
                            "insert": part
                        })
                    elif contentType == 'mark':
                        obj.append({
                            "attributes": {
                                "color": "#ee230d"
                            },
                            "insert": part
                        })
                    elif contentType == 'song':
                        obj.append({
                            "attributes": {
                                "color": "#0b84ed"
                            },
                            "insert": part
                        })
                    elif contentType == 'dance':
                        obj.append({
                            "attributes": {
                                "color": "#1DB100",
                            },
                            "insert": part
                        })
                    else:
                        obj.append({
                            "insert": part
                        })

            if len(contentParts) > 1:
                obj.append({
                    "attributes": {
                        "color": "#cccccc",
                    },
                    "insert": ' (手机端建议从评论回复中打开链接)'
                })

            obj.append({ "insert": "\n" })
            return (obj, len(tagContent) + 8)

    @staticmethod
    async def getTimelineJson(timeline: Timeline, info: VideoPartInfo, customTitle = '') -> Tuple[list, int]:
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
            (item_obj, item_len) = await TimelineConverter.getTimelineItemJson(item, info, customTitle)
            obj.extend(item_obj)
            content_len += item_len
        content_len += 1
        return (obj, content_len)

    @staticmethod
    async def getSeparateTimelineJson(timeline: Timeline, info: VideoPartInfo, customTitle = '') -> List[List]:
        """生成分条目的时间戳

        Args:
            timeline (Timeline): 时间轴
            info (VideoPartInfo): 视频信息

        Returns:
            List[List[str, list, int]]: _description_
        """
        results = []
        for item in timeline.items:
            (item_obj, item_len) = await TimelineConverter.getTimelineItemJson(item, info, customTitle)
            results.append([item.tag, item_obj, item_len])
        return results

    @staticmethod
    def loadTimelineFromCSV(path: str) -> Timeline:
        # before error:UnicodeDecodeError: 'gbk' codec can't decode byte 0x80 in position 4: illegal multibyte sequence
        with open(path, "r", encoding="utf-8-sig") as f:
            csv_l = f.readlines()
        its = [c.replace("\n", "").split(",") for c in csv_l]
        items = [TimelineItem(int(it[0]), it[1]) for it in its]
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
                    # 保存为毫秒
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
