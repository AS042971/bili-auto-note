from enum import Enum, unique
from typing import Iterator, List


@unique
class TimelineType(Enum):
    NORMAL = ''
    SONG = 'song'
    DANCE = 'dance'

@unique
class Member(Enum):
    AVA = 'a'
    BELLA = 'b'
    CAROL = 'c'
    DIANA = 'd'
    EILEEN = 'e'

class TimelineItem:
    def __init__(self,
                 sec: int, tag: str, highlight: bool = False,
                 type: TimelineType = TimelineType.NORMAL, members: List[Member] = []) -> None:
        """时间轴条目

        Args:
            sec (int): 条目秒数
            tag (str): 条目内容
            highlight (bool, optional): 是否高亮显示 Defaults to False.
            type (TimelineType, optional): 条目特殊类型，如歌舞等 Defaults to TimelineType.NORMAL.
            members (list[Member], optional): 特殊条目参与的成员 Defaults to [].
        """
        self.sec = sec
        self.tag = tag
        self.highlight = highlight
        self.type = type
        self.members = members

    def shift(self, delta: int) -> 'TimelineItem':
        """生成调整后的时间轴条目

        Args:
            delta (int): 调整的时间偏移量

        Returns:
            TimelineItem: 新生成的时间轴条目
        """
        return TimelineItem(self.sec + delta, self.tag, self.highlight, self.type, self.members)

    def __str__(self) -> str:
        m, s = divmod(self.sec, 60)
        h, m = divmod(m, 60)
        time = "%d:%02d:%02d" % (h, m, s)
        return time + ' ' + self.tag

class Timeline:
    def __init__(self, items: List[TimelineItem]) -> None:
        """生成时间轴

        Args:
            items (list[TimelineItem]): 时间轴条目
        """
        self.items = items
        self.items.sort(key=lambda item: item.sec)

    def __iter__(self) -> Iterator[TimelineItem]:
        return iter(self.items)

    def __add__(self, other: 'Timeline') -> 'Timeline':
        return Timeline(self.items + other.items)

    def shift(self, delta: int) -> 'Timeline':
        """生成调整后的时间轴

        Args:
            delta (int): 调整的时间偏移量

        Returns:
            Timeline: 新生成的时间轴
        """
        return Timeline([item.shift(delta) for item in self.items])

    def clip(self, start: int, length: int) -> 'Timeline':
        """生成时间轴切片

        Args:
            start (int): 切片开始对应的时刻（秒）
            length (int): 切片总长度

        Returns:
            Timeline: 适配于切片的时间轴（0表示切片开始时刻）
        """
        return Timeline([item.shift(-start) for item in self.items if item.sec >= start and item.sec <= start + length])

    def __str__(self) -> str:
        return '\n'.join(map(str, self.items))
