import aiohttp
import asyncio

# 复制得到的地址为 https://weibo.com/p/100103type%3D1%26q%3Dasoul
# 把里面的 100103 和 asoul 填到下面即可
containerid = '100103'
qword = 'asoul'

async def main():
    url = "https://m.weibo.cn/api/container/getIndex"
    headers = {
        "Referer": "https://m.weibo.cn",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1"
    }
    iter = 0
    while True:
        session = aiohttp.ClientSession(headers=headers)
        async with session.get(url, params={
                "jumpfrom": "weibocom",
                "containerid": containerid + "type=1",
                "q": qword
            }) as res:
            result = await res.json()
            iter += 1
            print(f'已刷新{iter}次')
        await session.close()
        # 等30s
        for _ in range(30):
            await asyncio.sleep(1)
            print('*', end='', flush=True)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
