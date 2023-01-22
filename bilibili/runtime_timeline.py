from .timeline import TimelineItem, Timeline
from typing import Iterator, List
from .note_object import NoteObject
from .video import VideoPartInfo
from .timeline_converter import TimelineConverter
from .pub_timeline_config import PubTimelineConfig
import time

class RuntimeTimelineItem:
    def __init__(self, item: TimelineItem, note_obj: NoteObject) -> None:
        self.item = item
        self.note_obj = note_obj
        self.time_obj = []
        self.part_names = []

    def registerPartInfo(self, info: VideoPartInfo, start_time: int, token_index: int, customTitle: str, hidePart: bool) -> None:
        local_sec = self.item.sec - start_time
        if local_sec < 0 or local_sec > info.duration:
            return
        self.part_names.append(info.title)
        if str(token_index) in self.item.mask:
            return
        desc = customTitle
        # 时间胶囊
        if hidePart:
            time_label = {
                "insert": {
                    "tag": {
                        "cid": info.cid,
                        "oid_type": 2,
                        "status": 0,
                        "index": info.index,
                        "seconds": local_sec,
                        "cidCount": 1,
                        "key": str(round(time.time()*1000)),
                        "title": "",
                        "epid": 0,
                        "desc": desc
                    }
                }
            }
        else:
            time_label = {
                "insert": {
                    "tag": {
                        "cid": info.cid,
                        "oid_type": 0,
                        "status": 0,
                        "index": info.index,
                        "seconds": local_sec,
                        "cidCount": info.cidCount,
                        "key": str(round(time.time()*1000)),
                        "title": "",
                        "epid": 0,
                        "desc": desc
                    }
                }
            }
        self.time_obj.append(time_label)

    def getObject(self) -> NoteObject:
        if not self.time_obj:
            return NoteObject()
        note_object = NoteObject()
        if not self.item.tag.startswith('##'):
            for i, o in enumerate(self.time_obj):
                note_object.append(o, 1)
                if i != len(self.time_obj) - 1:
                    note_object.append({
                        "attributes": { "color": "#cccccc" },
                        "insert": " "
                    }, 1)
            note_object.append({
                "attributes": { "color": "#cccccc" },
                "insert": " ⇙"
            }, 1)
            note_object.appendNewLine()
        note_object += self.note_obj
        return note_object

class RuntimeTimeline:
    def __init__(self, items: List[RuntimeTimelineItem]) -> None:
        self.items = items

    def __iter__(self) -> Iterator[RuntimeTimelineItem]:
        return iter(self.items)

    def songAndDance(self) -> 'RuntimeTimeline':
        """生成仅含歌舞的时间轴（🎤/💃开头的条目）

        Returns:
            Timeline: 仅含歌舞的时间轴
        """
        sd_items = list(filter(lambda item: item.item.tag.startswith('🎤') or item.item.tag.startswith('💃'), self.items))
        return RuntimeTimeline(sd_items)

    @staticmethod
    async def getRuntimeTimeline(timeline: Timeline, config: PubTimelineConfig) -> 'RuntimeTimeline':
        converted_items = []
        for item in timeline:
            note_obj = await TimelineConverter.getTimelineItemJson(item, config)
            converted_items.append(RuntimeTimelineItem(item, note_obj))
        return RuntimeTimeline(converted_items)

    def registerPartInfo(self, info: VideoPartInfo, start_time: int, token_index: int, customTitle: str, hidePart: bool) -> None:
        for item in self.items:
            item.registerPartInfo(info, start_time, token_index, customTitle, hidePart)