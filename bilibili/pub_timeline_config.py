from typing import Tuple, List

class TokenConfig:
    def __init__(self, json_data: dict) -> None:
        self.key: str = json_data['key'] if 'key' in json_data else ''
        self.offsets: list = json_data['offsets'] if 'offsets' in json_data else []
        self.marker: str = json_data['marker'] if 'marker' in json_data else ''
        self.jump_op_desc: str = json_data['jumpOpDesc'] if 'jumpOpDesc' in json_data else ''

class PubTimelineConfig:
    def __init__(self, json_data: dict) -> None:
        # 填充必要内容
        self.bvid: str = json_data['bvid']
        self.publish: bool = json_data['publish']
        self.cover: str = json_data['cover']
        self.tokens = [TokenConfig(data) for data in json_data['tokens']]

        # 填充可选内容
        self.custom_video_info: str = json_data['customVideoInfo'] if 'customVideoInfo' in json_data else ''
        self.ignore_threshold: int = json_data['ignoreThreshold'] if 'ignoreThreshold' in json_data else 600
        self.hide_part: bool = json_data['hidePart'] if 'hidePart' in json_data else False

        # 填充基础构架
        self.song_and_dance: bool = json_data['songAndDanceAbstract'] if 'songAndDanceAbstract' in json_data else False
        self.jumpOP: bool = json_data['jumpOP'] if 'jumpOP' in json_data else False
        self.preface: str = json_data['preface'] if 'preface' in json_data else ''
        self.img_cover: str = json_data['imgCover'] if 'imgCover' in json_data else ''
        self.img_footer: list = json_data['imgFooter'] if 'imgFooter' in json_data else []

        # 发布选项
        self.auto_comment: bool = json_data['autoComment'] if 'autoComment' in json_data else True
