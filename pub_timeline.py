#! /usr/bin/python3
from bilibili import BilibiliAgent, Timeline, TimelineItem, BilibiliNoteHelper, TimelineConverter
import asyncio
import sys
import json

async def main(config_path: str):
    with open(config_path,'r',encoding='utf8') as fp:
        json_data = json.load(fp)
        agent = BilibiliAgent(json_data['cookie'])
        bvid = json_data['bvid']
        offsets = json_data['offsets']
        cover = json_data['cover']
        publish = json_data['publish']
        timeline = TimelineConverter.loadTimelineFromCSV(json_data['timeline'])
        await BilibiliNoteHelper.sendNote(timeline, agent, bvid, offsets, cover, publish)
        await agent.close()

if __name__ == '__main__':
    # add default config filepath
    if len(sys.argv) == 1:
        st = "./config/pub_timeline.json"
        print(f'Loading default config file: {st}')
        try:
            with open(st, "r", encoding="utf-8") as f:
                pass
            print(f'Successfully loaded {st}')
        except FileNotFoundError as e_f:
            print(e_f)
            print('Usage: pub_timeline.py <path to config file>')
            sys.exit(-1)
    else:
        st = sys.argv[1]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main(st))
