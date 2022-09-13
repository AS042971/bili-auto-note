#!/usr/bin/python3
import sys
import asyncio
import json
from bilibili import BilibiliAgent

async def main(img_path: str, config_path: str):
    with open(config_path,'r',encoding='utf8') as fp:
        json_data = json.load(fp)
        agent = BilibiliAgent(json_data['cookie'])
        result = await agent.post('https://api.bilibili.com/x/note/image/upload', data={
            "file": open(img_path,"rb"),
            "csrf": agent.csrf
        })
        print(f'图片地址: "{result["location"]}"')
        await agent.close()

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print('Usage: image_uploader.py img_path <config_file_path>')
        sys.exit(-1)
    img = sys.argv[1]
    if len(sys.argv) < 3:
        st = "./config/pub_timeline.json"
        print(f'Loading default config file: {st}')
        try:
            with open(st, "r", encoding="utf-8") as f:
                pass
            print(f'Successfully loaded {st}')
        except FileNotFoundError as e_f:
            print(e_f)
            print('Usage: image_uploader.py img_path <config_file_path>')
            sys.exit(-1)
    else:
        st = sys.argv[2]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main(img, st))
