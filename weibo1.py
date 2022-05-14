import random
import aiohttp
import asyncio

records = []
cnt = 0

async def fetchUrl(session: aiohttp.ClientSession, pid, uid, max_id):

    url = "https://weibo.com/ajax/statuses/buildComments"

    params = {
        "flow" : 1,
        "is_reload" : 1,
        "id" : pid,
        "is_show_bulletin" : 2,
        "is_mix" : 0,
        "max_id" : max_id,
        "count" : 20,
        "uid" : uid,
    }

    async with session.get(url, params = params) as res:
        result = await res.json()
        return result

def parseJson(jsonObj):
    global cnt
    global records
    data = jsonObj["data"]
    for item in data:
        records.append(item['text_raw'])
    if len(records) > 100:
        cnt += len(records)
        with open("test.txt","a+", encoding="utf-8") as f:
            for item in records:
                f.write(item + '\n')
            records.clear()
    return jsonObj["max_id"]

async def main():
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
        "Cookie": "SCF=AggZcWsOfjA7qcNvcuzbEWCdUQDPgYFV0Fiq2Hgwttfn53hfHhmMZ35J38UU5Pw76ZCUubw-YRXGaaSdkMolmPo.; UOR=www.caixin.com,widget.weibo.com,www.ithome.com; SINAGLOBAL=1540012847980.5574.1610420805391; ULV=1652417302786:63:3:3:3839127239371.74.1652417302715:1652370352886; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WWLuv-PUHiqgX-SEqi1_L8a5JpX5KMhUgL.FozRe0-RSKqfeh-2dJLoI7pIIs8V9fvPHfUPHfMt; ALF=1683953185; WBPSESS=bkkEvMKSezDKXHLVsGXqpiUWm7kCiM_ZKiZSpxx2Q0CUxt6HiYtJNkrd9U_zwGOZg6DGH4RO1mvsJ92T8FZeJiJ7aIC98v0v8KLdLefJ8R8WmKM1rhalEYecBFS2_16z3R53vF5L_xnl3lwJwjj4VQ==; SUB=_2A25PeZL7DeRhGeRG6FcZ9SjJyzmIHXVsDoMzrDV8PUNbmtAfLRD7kW9NTdvpPVzHVT0GtDHoClTWZ6K7sjhswvp-; SSOLoginState=1652417195; _s_tentry=www.weibo.com; Apache=3839127239371.74.1652417302715; XSRF-TOKEN=_gG21-tkdgjceXRcvkcS5D-l"
    }
    session = aiohttp.ClientSession(headers=headers)
    pid = 4768632008346549		# 微博id，固定
    uid = 7745712344			# 用户id，固定
    # max_id 为 0 时爬取第一页，后续请求的 max_id 可以从前一条请求中解析得到
    max_id = 0
    while(True):
        html = await fetchUrl(session, pid, uid, max_id)
        # 解析数据的时候，动态改变 max_id 的值
        new_max_id = parseJson(html)
        print(f'已爬取{cnt + len(records)}条记录, 当前id: {new_max_id}')
        if new_max_id == 0:
            print('触发反爬虫机制，等待5s')
            await asyncio.sleep(5)
        else:
            max_id = new_max_id
        await asyncio.sleep(0.2)
    await session.close()

if __name__ == '__main__':
    # add default config filepath

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())