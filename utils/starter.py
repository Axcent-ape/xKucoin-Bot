import os
import random

from utils.x_kucoin import xKucoin
from data import config
from utils.core import logger
import datetime
import pandas as pd
from utils.core.telegram import Accounts
import asyncio


async def start(thread: int, session_name: str, phone_number: str, proxy: [str, None]):
    kucoin = xKucoin(session_name=session_name, phone_number=phone_number, thread=thread, proxy=proxy)
    account = session_name + '.session'

    try:
        await kucoin.login()

        summary = await kucoin.summary()
        logger.success(f'Thread {thread} | {account} | Balance: {summary.get("availableAmount")}')

        if summary.get('needToCheck'):
            if await kucoin.obtain():
                logger.success(f"Thread {thread} | {account} | Claim first reward!")

        energy = summary.get('feedPreview').get('molecule')

        while True:
            clicks = random.randint(*config.CLICKS_PER_REQUEST)
            if energy >= clicks:
                if await kucoin.increase(clicks, energy-clicks):
                    logger.success(f"Thread {thread} | {account} | Sent {clicks} clicks")
                else:
                    logger.warning(f"Thread {thread} | {account} | Couldn't send {clicks} clicks; energy: {energy}")
                sleep = random.uniform(*config.DELAYS['SEND_CLICKS'])

            else:
                sleep = 60

            energy += int(sleep)
            await asyncio.sleep(sleep)

        await kucoin.logout()

    except Exception as e:
        logger.error(f"Thread {thread} | {account} | Error: {e}")


async def stats():
    accounts = await Accounts().get_accounts()

    tasks = []
    for thread, account in enumerate(accounts):
        session_name, phone_number, proxy = account.values()
        tasks.append(asyncio.create_task(xKucoin(session_name=session_name, phone_number=phone_number, thread=thread, proxy=proxy).stats()))

    data = await asyncio.gather(*tasks)

    path = f"statistics/statistics_{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.csv"
    columns = ['Phone number', 'Name', 'Balance', 'Wallet Connected', 'Proxy (login:password@ip:port)']

    if not os.path.exists('statistics'): os.mkdir('statistics')
    df = pd.DataFrame(data, columns=columns)
    df.to_csv(path, index=False, encoding='utf-8-sig')

    logger.success(f"Saved statistics to {path}")