#!/usr/bin/python3
import sys
import json
import re
from bilibili import Timeline, TimelineItem, TimelineConverter

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
    time_line = TimelineConverter.loadTimelineFromText(parts[0]).shift(offsets[0])
    if len(parts) >= 2:
        for i in range(len(parts))[1:]:
            time_line += TimelineConverter.loadTimelineFromText(parts[i]).shift(offsets[i])
    if TimelineConverter.saveTimelineToCSV(out, time_line):
        print("Done!")
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
