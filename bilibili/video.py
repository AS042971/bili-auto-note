class VideoPartInfo:
  def __init__(self, cid: int, index: int, cidCount: int, title: str, duration: int) -> None:
    """视频分P信息

    Args:
        cid (int): 唯一标识符
        index (int): 分P序号（从1开始）
        cidCount (int): 总共的分P数量
        title (str): 分P标题
    """
    self.cid = cid
    self.index = index
    self.cidCount = cidCount
    self.title = title
    self.duration = duration

class VideoInfo:
  def __init__(self, aid: int, pic: str, title: str, parts: list[VideoPartInfo]) -> None:
    """视频信息

    Args:
        aid (int): 视频AV号
        pic (str): 视频封面图
        title (str): 视频标题
        parts (list[VideoPartInfo]): 每个分P的信息
    """
    self.aid = aid
    self.pic = pic
    self.title = title
    self.parts = parts
