import re
import aiohttp

class BilibiliAgent:
    def __init__(self, cookie: str) -> None:
        self.uid = None
        self.csrf = None
        if "bili_jct=" in cookie and "SESSDATA=" in cookie:
            self.csrf = re.search(r"bili_jct=([0-9a-zA-Z]{32})", cookie).group(1).strip()
            self.cookie = cookie
        else:
            raise Exception("cookie 无效\n请保证有SESSDATA字段和bili_jct字段")
        self.headers = {
            "Referer": "https://www.bilibili.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/83.0.4103.116 Safari/537.36",
            "Cookie": self.cookie,
        }
        self.session = aiohttp.ClientSession(headers=self.headers)

    @staticmethod
    def _check(url: str, res_json) -> None:
        if res_json["code"] != 0:
            raise Exception(f"服务调用失败\n地址: {url}\n返回值: {res_json}")

    async def get(self, url: str, **kwargs) -> dict:
        async with self.session.get(url, **kwargs) as res:
            res_json = await res.json()
            BilibiliAgent._check(url, res_json)
            return res_json.get("data", {})

    async def post(self, url: str, **kwargs) -> dict:
        async with self.session.post(url, **kwargs) as res:
            res_json = await res.json()
            BilibiliAgent._check(url, res_json)
            return res_json.get("data", {})
