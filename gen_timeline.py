#! /usr/bin/python3
import sys
import json
import re
from bilibili import Timeline, TimelineItem


def check_file(files: list):
    """
    检查填写配置中的文件是否真实存在
    :param files: 文件名列表
    :return: file_name/None
    """
    for file in files:
        try:
            with open(file, "r", encoding="utf-8"):
                pass
        except FileNotFoundError as e:
            # print(e)
            print(f"Error: No such file or directory: {file}\nPlease check gen_timeline.json!")
            return file


def txt2tl(path: str) -> Timeline:
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
            li_re = re.findall("(.+?\d+:\d+) ?(.+)", li.strip())[0]
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
    return items


def tl2csv(path: str, items: Timeline):
    """
    时间轴Timeline数据保存为csv文件
    :param path: csv保存路径
    :param items: Timeline
    :return: bool
    """
    try:
        # "utf-8-sig"的原因：能在excel中正确显示
        with open(path, "w", encoding="utf-8-sig") as f:
            for item in items:
                # 保存为秒
                f.write(f"{item.sec},{item.tag},{int(item.highlight)}\n")
                # f.write(f"{item.sec},{item.tag},{int(item.highlight),{item.type},{' '.join(item.members)}\n")
                # 保存为\d+?:?\d+:\d+的格式
                # f.write(f"{item.__str__().split(' ')[0]},{item.tag},{int(item.highlight)\n")
                # f.write(f"{item.__str__().split(' ')[0]},{item.tag},{int(item.highlight),{item.type},{item.members}\n")
    except Exception as e:
        print(e)
        return False
    return True


def main(config_path: str):
    with open(config_path, 'r', encoding='utf8') as fp:
        json_data = json.load(fp)
        print(json_data)
        offsets = json_data['offsets']
        parts = json_data['parts']
        out = json_data['out']
    if check_file(parts) is not None:
        sys.exit(-1)
    if len(parts) != len(offsets):
        print("参数offsets和parts个数不同，无法继续")
        sys.exit(-1)
    time_line = Timeline(txt2tl(parts[0])).shift(offsets[0])
    if len(parts) >= 2:
        for i in range(len(parts))[1:]:
            time_line = time_line.__add__(Timeline(txt2tl(parts[i])).shift(offsets[i]))
    if tl2csv(path=out, items=time_line):
        print("Done！")
    else:
        print("Save to .csv failed")


if __name__ == '__main__':
    # add default config filepath
    if len(sys.argv) == 1:
        st = "./config/gen_timeline.json"
        print(f'Loading default config file: {st}')
        try:
            with open(st, "r", encoding="utf-8") as f:
                pass
            print(f'Successfully loaded {st}')
        except FileNotFoundError as e_f:
            print(e_f)
            print('Usage: gen_timeline.py <path to config file>')
            sys.exit(-1)
    else:
        st = sys.argv[1]

    main(st)
