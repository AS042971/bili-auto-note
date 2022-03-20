

from bilibili import BilibiliAgent, Timeline, TimelineItem, BilibiliNoteHelper, VideoPartInfo
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
    timeline = BilibiliNoteHelper.loadTimeline(json_data['timeline'])
    await BilibiliNoteHelper.sendNote(timeline, agent, bvid, offsets, cover, publish)

if __name__ == '__main__':
  if len(sys.argv) == 1:
    print('Usage: bilinote.py <path to config file>')
    sys.exit(-1)

  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)
  loop.run_until_complete(main(sys.argv[1]))
