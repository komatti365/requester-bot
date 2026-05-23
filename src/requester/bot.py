# NOTE : This program requires the 'message_content' intent.

import discord
import logging
from decouple import AutoConfig, Config, RepositoryEnv, UndefinedValueError
from requests import post
from .nicoVideo import NicoVideo
import os

_env_path = os.environ.get("REQBOT_ENV_PATH")
if _env_path:
    config = Config(RepositoryEnv(_env_path))
else:
    config = AutoConfig(os.getcwd())

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


# SECTION - イベント定義


@client.event
async def on_ready():
    logger = logging.getLogger(__name__)
    logger.info(f'We have logged in as {client.user}')
    logo = r"""
    _  _ _  _ ____ ____ ____ ____ _  _
    |\ | |  | |    |  | [__  |___ |\ |
    | \| |__| |___ |__| ___] |___ | \|
    ____ ____ ____    ___  ____ ___
    |__/ |___ |  | __ |__] |  |  |
    |  \ |___ |_\|    |__] |__|  |
    """.splitlines()

    for l in logo:
        logger.info(l)


@client.event
async def on_message(message: discord.Message):
    """メッセージ受信イベント

    受信したメッセージのうち、
        1. 自身が送信したものではなく
        2. テキストチャンネル宛に送信されたもので
        3. チャンネルIDが監視対象と一致するもの
    を処理対象とし、
    メッセージをNicoVideoオブジェクトに変換したのち、
    実在するものはリクエストDBに送信した上でリプライ、
    実在しないものはリアクションを追加します

    Args:
        message (discord.Message): 処理するメッセージオブジェクト
    """
    targetChannelId = int(config("REQBOT_WATCH_CHANNEL"))
    if (
        message.author != client.user
        and isinstance(message.channel, discord.TextChannel)
        and message.channel.id == targetChannelId
    ):
        video = NicoVideo(message.content)
        if not video.isExists:
            if video.id != "sm0":
                await message.add_reaction("\u2754")
            return
        postRequest(video)
        successEmbed = getSuccessEmbed(
            videoTitle=video.title or "（タイトル不明）",
            watchUrl=video.watchUrl or "",
            thumbnailUrl=video.thumbnailUrl or
            "https://placehold.jp/333333/cccccc/130x100.png?text=サムネイル%0A取得エラー"
        )
        await message.reply(embed=successEmbed)


# !SECTION - イベント定義　ここまで


def getSuccessEmbed(videoTitle: str, watchUrl: str, thumbnailUrl: str) -> discord.Embed:
    result = discord.Embed()
    result.set_author(name="受付成功：")
    result.title = videoTitle
    result.description = "この動画のリクエストを受け付けました。"
    result.url = watchUrl
    result.colour = discord.Colour.green()
    result.set_thumbnail(url=thumbnailUrl)
    result.set_footer(text="Powered by NUCOSen")
    return result


def startDiscordBot():
    DISCORD_TOKEN = config("REQBOT_TOKEN")
    client.run(str(DISCORD_TOKEN))


def postRequest(item: NicoVideo):
    """リクエストをDBに送信する

    Args:
        item (NicoVideo): NicoVideoオブジェクト
    """
    # Get API key from file if specified, otherwise from config
    db_key_file = os.environ.get("REQBOT_DB_KEY_FILE")
    db_key = None
    if db_key_file and os.path.exists(db_key_file):
        with open(db_key_file, "r", encoding="utf-8") as f:
            db_key = f.read().strip()
    if not db_key:
        db_key = config("REQBOT_DB_KEY", cast=str, default="")
        
    headers = {
        'x-apikey': db_key,
        'cache-control': "no-cache"
    }
    resp = post(
        # NOTE - Url MUST be str.
        url=config("REQBOT_DB_URI", cast=str),  # type: ignore
        json={"videoId": str(item)}, headers=headers,
        timeout=60
    )
    resp.raise_for_status()
