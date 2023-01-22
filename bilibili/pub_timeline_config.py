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

        if 'tokens' not in json_data and 'offsets' in json_data:
            print('建议更新配置文件并使用tokens来标记不同类型的分P，详见README')
            self.tokens = []
            if 'danmakuOffsets' in json_data:
                self.tokens.append(TokenConfig({
                    'key': '弹幕',
                    'offsets': json_data['danmakuOffsets'],
                    'marker': '弹',
                    'jumpOpDesc': '🪂点此跳过OP (弹幕版)'
                }))
            self.tokens.append(TokenConfig({
                    'key': '',
                    'offsets': json_data['offsets'],
                    'marker': '',
                    'jumpOpDesc': '🪂点此跳过OP (纯净版)'
                }))
        else:
            self.tokens = [TokenConfig(data) for data in json_data['tokens']]

        # 填充可选内容
        self.custom_video_info: str = json_data['customVideoInfo'] if 'customVideoInfo' in json_data else ''
        self.ignore_threshold: int = json_data['ignoreThreshold'] if 'ignoreThreshold' in json_data else 600
        self.hide_part: bool = json_data['hidePart'] if 'hidePart' in json_data else False

        # 填充基础构架
        if 'songAndDanceAbstract' in json_data or 'jumpOP' in json_data or 'preface' in json_data or 'imgCover' in json_data or 'imgFooter' in json_data:
            print('注意：配置字 songAndDanceAbstract/jumpOP/preface/imgCover/imgFooter 已不再使用，请在template内添加')

        # 样式选项
        self.title_prefix: str = json_data['titlePrefix'] if 'titlePrefix' in json_data else '[AC|b#fff359|s18]'
        self.title_postfix: str = json_data['titlePostfix'] if 'titlePostfix' in json_data else ''
        self.sub_title_prefix: str = json_data['subTitlePrefix'] if 'subTitlePrefix' in json_data else '[AC|B]'
        self.sub_title_postfix: str = json_data['subTitlePostfix'] if 'subTitlePostfix' in json_data else ''
        self.song_dance_title: str = json_data['songDanceTitle'] if 'songDanceTitle' in json_data else '[AC|B|b#ffa0d0|s18]　　　本场歌舞快速导航　　　'

        # 发布选项
        self.auto_comment: bool = json_data['autoComment'] if 'autoComment' in json_data else True
