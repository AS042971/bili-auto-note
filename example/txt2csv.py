#! /usr/bin/python3
# -*- coding = utf-8 -*-
# @Python : 3.8

import os
import re


def txt2csv(path):
    if path[-1] != "/":
        path += "/"
    files = os.listdir(path)
    files = [f for f in files if "txt" in f]
    if len(files) == 0:
        print("指定目录下无txt文件，请检查重试")
        exit(0)
    lines = []
    for fp in files:
        with open(path + fp, "r", encoding="utf-8") as f:
            for line in f.readlines():
                lines.append(line.replace("\n", ""))
    with open(path + "timeline.csv", "w", encoding="utf-8-sig") as f:
        for li in lines:
            try:
                li_re = re.findall("(.+?\d+:\d+) ?(.+)", li.strip())[0]
            except:
                print(f"Please check (line{lines.index(li)}:{li}),continue...")
                continue
            if li_re[1][-1] == "*":
                text = f"{li_re[0]},{li_re[1][:-1].replace(',', '，')},1\n"
            else:
                text = f"{li_re[0]},{li_re[1].replace(',', '，')},0\n"
            f.write(text)
    print(f"Done,file path: {path + 'timeline.csv'}")
    return True


txt2csv("./data")
