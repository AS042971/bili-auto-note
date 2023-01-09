from enum import Enum, unique
from typing import Iterator, List

class TimelineItem:
    def __init__(self,
                 sec: int, tag: str, key=None, mask='') -> None:
        """时间轴条目

        Args:
            sec (int): 条目秒数
            tag (str): 条目内容
        """
        self.sec = sec
        self.tag = tag.strip()
        self.mask = mask
        if key:
            self.key = key
        else:
            self.key = f'{self.sec}_{self.tag}'

    def shift(self, delta: int) -> 'TimelineItem':
        """生成调整后的时间轴条目

        Args:
            delta (int): 调整的时间偏移量

        Returns:
            TimelineItem: 新生成的时间轴条目
        """
        return TimelineItem(self.sec + delta, self.tag, self.key, self.mask)

    def __str__(self) -> str:
        m, s = divmod(self.sec, 60)
        h, m = divmod(m, 60)
        if h == 0:
            time = "%02d:%02d" % (m, s)
        else:
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

    def __str__(self) -> str:
        return '\n'.join(map(str, self.items))

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

    def songAndDance(self) -> 'Timeline':
        """生成仅含歌舞的时间轴（🎤/💃开头的条目）

        Returns:
            Timeline: 仅含歌舞的时间轴
        """
        sd_items = list(filter(lambda item: item.tag.startswith('🎤') or item.tag.startswith('💃'), self.items))
        return Timeline(sd_items)

    def section(self) -> 'Timeline':
        """生成仅含章节的时间轴（##开头的条目）

        Returns:
            Timeline: 仅含章节的时间轴
        """
        sd_items = list(filter(lambda item: item.tag.startswith('##')), self.items)
        return Timeline(sd_items)

    def hasTitle(self) -> bool:
        """判断轴中是否包含章节标题（##开头的条目）

        Returns:
            bool: 是否包含章节标题
        """
        for item in self.items:
            if item.tag.startswith('##'):
                return True
        return False
