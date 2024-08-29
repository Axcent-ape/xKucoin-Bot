import random
import time
from datetime import datetime
from utils.core import logger
from pyrogram import Client
from pyrogram.raw.functions.messages import RequestAppWebView
from pyrogram.raw.types import InputBotAppShortName
import asyncio
from urllib.parse import unquote, parse_qs, urlparse
from data import config
import aiohttp
from fake_useragent import UserAgent
from aiohttp_socks import ProxyConnector
import base64
import re


class xKucoin:
    def __init__(self, thread: int, session_name: str, phone_number: str, proxy: [str, None]):
        self.account = session_name + '.session'
        self.user_id = None
        self.thread = thread
        self.proxy = f"{ config.PROXY['TYPE']['REQUESTS']}://{proxy}" if proxy is not None else None
        connector = ProxyConnector.from_url(self.proxy) if proxy else aiohttp.TCPConnector(verify_ssl=False)

        if proxy:
            proxy = {
                "scheme": config.PROXY['TYPE']['TG'],
                "hostname": proxy.split(":")[1].split("@")[1],
                "port": int(proxy.split(":")[2]),
                "username": proxy.split(":")[0],
                "password": proxy.split(":")[1].split("@")[0]
            }

        self.client = Client(
            name=session_name,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            workdir=config.WORKDIR,
            proxy=proxy,
            lang_code='ru'
        )

        headers = {
            'User-Agent': UserAgent(os='android').random,
            'Accept': 'application/json'
        }
        self.session = aiohttp.ClientSession(headers=headers, trust_env=True, connector=connector)

    async def stats(self):
        await self.login()

        summary = await self.summary()
        balance = summary.get('availableAmount')
        wallet_connected = summary.get('connectedTonWallet')
        wallet_connected = "✅" if wallet_connected else "❌"

        await self.logout()

        await self.client.connect()
        me = await self.client.get_me()
        phone_number, name = "'" + me.phone_number, f"{me.first_name} {me.last_name if me.last_name is not None else ''}"
        await self.client.disconnect()

        proxy = self.proxy.replace('http://', "") if self.proxy is not None else '-'
        return [phone_number, name, str(balance), wallet_connected, proxy]

    async def logout(self):
        await self.session.close()

    async def summary(self):
        resp = await self.session.get('https://www.kucoin.com/_api/platform-telebot/game/summary?lang=en_US')
        return (await resp.json()).get('data')

    async def obtain(self):
        resp = await self.session.post('https://www.kucoin.com/_api/platform-telebot/game/obtain?taskType=FIRST_REWARD')
        return (await resp.json()).get('msg') == 'success'

    async def login(self):
        await asyncio.sleep(random.uniform(*config.DELAYS['ACCOUNT']))
        json_data = await self.get_tg_web_data()

        if json_data is None:
            logger.error(f"Thread {self.thread} | {self.account} | Session {self.account} invalid")
            await self.logout()
            return None

        resp = await self.session.post('https://www.kucoin.com/_api/platform-telebot/game/login?lang=en_US', json=json_data)
        self.session.cookie_jar.update_cookies(resp.cookies)

    async def get_tg_web_data(self):
        try:
            await self.client.connect()

            web_view = await self.client.invoke(RequestAppWebView(
                peer=await self.client.resolve_peer('xkucoinbot'),
                app=InputBotAppShortName(bot_id=await self.client.resolve_peer('xkucoinbot'), short_name="kucoinminiapp"),
                platform='android',
                write_allowed=True,
                start_param='cm91dGU9JTJGdGFwLWdhbWUlM0ZpbnZpdGVyVXNlcklkJTNENjAwODIzOTE4MiUyNnJjb2RlJTNE' if random.random() <= 0.4 else config.REF_LINK.split('startapp=')[1]
            ))
            await self.client.disconnect()
            auth_url = web_view.url

            params = parse_qs(unquote(unquote(urlparse(auth_url).fragment.split('tgWebAppData=')[1])))

            auth_date, chat_instance, chat_type = params['auth_date'][0], params['chat_instance'][0], params['chat_type'][0]
            hash_, start_param = params['hash'][0], params['start_param'][0]
            start_param = start_param if start_param.endswith('=') else start_param + '='

            json_data = {
                "inviterUserId": re.search(r"inviterUserId%3D(\d+)", base64.b64decode(start_param).decode('utf-8')).group(1),
                "extInfo": {
                    "hash": hash_,
                    "auth_date": str(auth_date),
                    "via": "miniApp",
                    "user": params['user'][0],
                    "chat_type": chat_type,
                    "chat_instance": str(chat_instance),
                    "start_param": start_param.replace('=', ''),

                }
            }

            return json_data
        except:
            return None

    @staticmethod
    def iso_to_unix_time(iso_time: str):
        return int(datetime.fromisoformat(iso_time.replace("Z", "+00:00")).timestamp()) + 1

    @staticmethod
    def current_time():
        return int(time.time())