import random
import sys
import json
import aiohttp
import asyncio
import datetime

def delta2str(delta: float) -> str:
    m, s = divmod(delta, 60)
    h, m = divmod(m, 60)
    return "%02d:%02d:%02d" % (h, m, s)

async def parseFile(jsonl_path: str):
    dm_cnt = 0
    sc_cnt = 0
    total_cnt = 0
    start_time = None
    dm_list = []
    sc_list = []
    users = {}

    with open(jsonl_path, "r", encoding="utf-8") as ifile:
        while True:
            line = ifile.readline()
            total_cnt += 1
            if (total_cnt % 1000 == 0):
                print(f'已处理{total_cnt}条数据，其中共{dm_cnt}条弹幕和{sc_cnt}条SC')
            if not line:
                break

            if not start_time:
                # 首条数据，读取时间
                live_obj = json.loads(line)
                start_time = live_obj['live_time']

            elif line[9:18] == 'DANMU_MSG':
                raw_dm_obj = json.loads(line)
                dm_cnt += 1
                info = raw_dm_obj['info']
                dm_time = info[0][4]
                delta_time = dm_time / 1000 - start_time
                content = info[1].strip()
                uid = info[2][0]
                # if uid not in users:
                #     users[uid] = None
                uname = info[2][1]
                dm_list.append((delta_time, uid, uname, content))

            elif line[8:28] == '"SUPER_CHAT_MESSAGE"':
                raw_sc_obj = json.loads(line)
                sc_cnt += 1
                data = raw_sc_obj['data']
                sc_time = data['start_time']
                delta_time = sc_time - start_time
                price = data['price']
                uid = data['uid']
                uname = data['user_info']['uname']
                message = data['message']
                if uid not in users:
                    users[uid] = None
                sc_list.append((delta_time, uid, uname, message, price))

    print(f'存储{dm_cnt}条弹幕中')
    print(f'共{len(users)}个发SC用户')

    headers = {
        "Referer": "https://www.bilibili.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/83.0.4103.116 Safari/537.36"
    }
    url = 'https://account.bilibili.com/api/member/getCardByMid'
    session = aiohttp.ClientSession(headers=headers)

    print(f'正在获取用户信息，预计需要{len(users) / 5}秒')
    for index, uid in enumerate(users.keys()):
        async with session.get(url, params={
            'mid': uid
        }) as res:
            result = await res.json()
            regtime = result['card']['regtime']
            level = result['card']['level_info']['current_level']
            users[uid] = (regtime, level)
            await asyncio.sleep(0.05)
        if (index % 10 == 0):
            print(f'{index} / {len(users)}')
    await session.close()

    with open('dm.csv', "w", encoding="utf-8-sig") as f:
        f.write("时间,UID,用户名,弹幕内容\n")
        for item in dm_list:
            uid = item[1]
            f.write(f"{delta2str(item[0])},{uid},{item[2].replace(',','，')},{item[3].replace(',','，')}\n")

    with open('sc.csv', "w", encoding="utf-8-sig") as f:
        f.write("时间,UID,用户名,注册时间,用户等级,SC内容,金额\n")
        for item in sc_list:
            uid = item[1]
            reg_time = users[uid][0]
            level_info = users[uid][1]
            sc_content = item[3].replace(',','，').replace('\n','')
            f.write(f"{delta2str(item[0])},{uid},{item[2].replace(',','，')},{datetime.datetime.fromtimestamp(reg_time)},{level_info},{sc_content},{item[4]}\n")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        print(f'Usage: json2csv.py path_to.jsonl')
        sys.exit(-1)
    else:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(parseFile(sys.argv[1]))
