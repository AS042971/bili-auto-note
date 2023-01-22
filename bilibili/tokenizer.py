from enum import Enum
from dataclasses import dataclass
from typing import List
import re
from .note_object import NoteObject
from .agent import BilibiliAgent
import time

async def getBvTitle(bvid: str) -> str:
    agent = BilibiliAgent()
    video_info_res = await agent.get(
        "https://api.bilibili.com/x/web-interface/view",
        params={
            "bvid": bvid
    })
    await agent.close()
    return video_info_res['title']

class TokenType(Enum):
    TEXT          = 0
    NEW_LINE      = 1

    URL           = 10
    BV_URL        = 11
    IMAGE         = 12

    SET_COLOR     = 20
    SET_BG        = 21

    SET_BOLD      = 30
    SET_ITALIC    = 31
    SET_UNDERLINE = 32
    SET_STRIKE    = 33

    ALIGN_LEFT    = 40
    ALIGN_CENTER  = 41
    ALIGN_RIGHT   = 42

    SET_FONT_SIZE = 50

    RESET         = 100

@dataclass
class Token:
    token_type: TokenType
    extra_info: str

def tokenizer(item: str) -> List[Token]:
    tokens = []
    current_str = item

    # 兼容旧式标记的预处理
    if current_str.endswith('**'):
        tokens.append(Token(TokenType.SET_COLOR, "#ee230d"))
        tokens.append(Token(TokenType.SET_BOLD, ""))
        current_str = current_str[:-2]
    elif current_str.endswith('*'):
        tokens.append(Token(TokenType.SET_COLOR, "#ee230d"))
        current_str = current_str[:-1]
    elif current_str.startswith('🎤'):
        tokens.append(Token(TokenType.SET_COLOR, "#0b84ed"))
    elif current_str.startswith('💃'):
        tokens.append(Token(TokenType.SET_COLOR, "#017001"))

    current_token = Token(TokenType.TEXT, "")
    while current_str:
        if current_str.startswith('[') or current_str.startswith('http') or current_str.startswith('BV'):
            # 装入上一个Token
            tokens.append(current_token)
            # 准备一个新的Token容器
            current_token = Token(TokenType.TEXT, "")
            if current_str.startswith('['):
                # 生成控制token
                token_end = current_str.find(']')
                if token_end != -1:
                    token_str = current_str[1:token_end]
                    token_items = token_str.split('|')
                    for item in token_items:
                        item = item.strip()
                        if item == 'N':
                            tokens.append(Token(TokenType.NEW_LINE, ""))
                        if item == 'R':
                            tokens.append(Token(TokenType.RESET, ""))
                        if item == 'B':
                            tokens.append(Token(TokenType.SET_BOLD, ""))
                        if item == 'I':
                            tokens.append(Token(TokenType.SET_ITALIC, ""))
                        if item == 'U':
                            tokens.append(Token(TokenType.SET_UNDERLINE, ""))
                        if item == 'S':
                            tokens.append(Token(TokenType.SET_STRIKE, ""))
                        if item == 'AL':
                            tokens.append(Token(TokenType.ALIGN_LEFT, ""))
                        if item == 'AC':
                            tokens.append(Token(TokenType.ALIGN_CENTER, ""))
                        if item == 'AR':
                            tokens.append(Token(TokenType.ALIGN_RIGHT, ""))
                        if item.startswith('#'):
                            tokens.append(Token(TokenType.SET_COLOR, item))
                        if item.startswith('b#'):
                            tokens.append(Token(TokenType.SET_BG, item[1:]))
                        if item.startswith('s'):
                            tokens.append(Token(TokenType.SET_FONT_SIZE, item[1:]))
                        if item.startswith('i'):
                            tokens.append(Token(TokenType.IMAGE, item[1:]))
                    current_str = current_str[token_end+1:]
                    continue
            if current_str.startswith('http'):
                token_end = current_str.find(' ')
                if token_end == -1:
                    url = current_str
                    current_str = ''
                else:
                    url = current_str[:token_end]
                    current_str = current_str[token_end+1:]
                tokens.append(Token(TokenType.URL, url))
                continue
            if current_str.startswith('BV'):
                bv_part = current_str[0:13]
                if re.match('BV[A-Za-z0-9]{10}', bv_part):
                    tokens.append(Token(TokenType.BV_URL, bv_part))
                    current_str = current_str[13:]
                    continue

        # 装入下一段
        next_bracket = current_str.find('[', 1)
        next_url = current_str.find('http', 1)
        next_bv = current_str.find('BV', 1)
        min_next = 10000
        if next_bracket != -1:
            min_next = min(min_next, next_bracket)
        if next_url != -1:
            min_next = min(min_next, next_url)
        if next_bv != -1:
            min_next = min(min_next, next_bv)
        str_part = current_str[:min_next]
        current_token.extra_info += str_part
        current_str = current_str[min_next:]
    tokens.append(current_token)
    return tokens

async def getContentJson(item: str) -> NoteObject:
    note_obj = NoteObject()
    tokens = tokenizer(item)
    align = None
    current_color = None
    current_bg = None
    current_size = None
    current_bold = False
    current_italic = False
    current_strike = False
    current_underline = False
    has_link = False

    for token in tokens:
        if token.token_type == TokenType.TEXT:
            if not token.extra_info:
                continue
            attributes = {}
            if current_color:
                attributes['color'] = current_color
            if current_bold:
                attributes['bold'] = True
            if current_italic:
                attributes['italic'] = True
            if current_strike:
                attributes['strike'] = True
            if current_underline:
                attributes['underline'] = True
            if align:
                attributes['align'] = align
            if current_bg:
                attributes['background'] = current_bg
            if current_size:
                attributes['size'] = current_size
            note_obj.append({
                "attributes": attributes,
                "insert": token.extra_info
            }, len(token.extra_info))
            continue
        elif token.token_type == TokenType.NEW_LINE:
            note_obj.appendNewLine(align)
            continue
        elif token.token_type == TokenType.URL:
            has_link = True
            attributes = {
                "color": "#0b84ed",
                "link": token.extra_info
            }
            if align:
                attributes['align'] = align
            note_obj.append({
                "attributes": attributes,
                "insert": '🔗打开链接'
            }, 1)
            continue
        elif token.token_type == TokenType.BV_URL:
            has_link = True
            title = await getBvTitle(token.extra_info)
            title = '▶️' + title
            attributes = {
                "color": "#0b84ed",
                "link": "https://www.bilibili.com/video/" + token.extra_info
            }
            if align:
                attributes['align'] = align
            note_obj.append({
                "attributes": attributes,
                "insert": title
            }, len(title))
            continue
        elif token.token_type == TokenType.IMAGE:
            note_obj.append({
                "insert": {
                    "imageUpload": {
                        "url": "//api.bilibili.com/x/note/image?image_id=" + token.extra_info,
                        "status": "done",
                        "width": 315,
                        "id": "IMAGE_" + str(round(time.time()*1000)),
                        "source": "video"
                    }
                }
            }, 1)
        elif token.token_type == TokenType.SET_BOLD:
            current_bold = True
            continue
        elif token.token_type == TokenType.SET_COLOR:
            current_color = token.extra_info
            continue
        elif token.token_type == TokenType.SET_BG:
            current_bg = token.extra_info
            continue
        elif token.token_type == TokenType.SET_ITALIC:
            current_italic = True
            continue
        elif token.token_type == TokenType.SET_STRIKE:
            current_strike = True
            continue
        elif token.token_type == TokenType.SET_UNDERLINE:
            current_underline = True
            continue
        elif token.token_type == TokenType.SET_FONT_SIZE:
            current_size = token.extra_info + 'px'
            continue
        elif token.token_type == TokenType.ALIGN_LEFT:
            align = None
            continue
        elif token.token_type == TokenType.ALIGN_CENTER:
            align = 'center'
            continue
        elif token.token_type == TokenType.ALIGN_RIGHT:
            align = 'right'
            continue
        elif token.token_type == TokenType.RESET:
            current_bold = False
            current_italic = False
            current_strike = False
            current_underline = False
            current_bg = None
            current_color = None
            current_size = None
            continue
    if has_link:
        note_obj.append({
            "attributes": {
                "color": "#cccccc",
            },
            "insert": ' (手机端建议从评论回复中打开链接)'
        }, 18)
    note_obj.appendNewLine(align)
    return note_obj
