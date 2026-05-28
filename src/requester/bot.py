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
tree = discord.app_commands.CommandTree(client)


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

    try:
        synced = await tree.sync()
        logger.info(f"Successfully synced {len(synced)} application command(s) globally.")
    except Exception as e:
        logger.error(f"Failed to sync application commands: {e}")


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


# SECTION - スラッシュコマンド定義

@tree.command(name="nowplaying", description="現在放送中の動画を表示します")
async def nowplaying_cmd(interaction: discord.Interaction):
    db_uri = config("REQBOT_DB_URI", cast=str)
    if db_uri.endswith("/requests"):
        nowplaying_uri = db_uri[:-9] + "/nowplaying"
    else:
        nowplaying_uri = db_uri + "/nowplaying"
        
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
    
    try:
        import asyncio
        from requests import get
        resp = await asyncio.to_thread(get, url=nowplaying_uri, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        item = None
        if isinstance(data, list) and len(data) > 0:
            item = data[0]
        elif isinstance(data, dict) and data:
            item = data
            
        if not item or not item.get("videoId"):
            await interaction.response.send_message("🎵 現在放送中の曲はありません。", ephemeral=True)
            return
            
        video_id = item["videoId"]
        title = item.get("title", "（タイトル不明）")
        duration = item.get("duration", 0)
        remaining = item.get("remainingTime", 0)
        
        watch_url = f"https://www.nicovideo.jp/watch/{video_id}"
        thumbnail_url = f"https://nicovideo.cdn.nimg.jp/thumbnails/{video_id[2:]}/{video_id[2:]}" if video_id.startswith("sm") else ""
        if not thumbnail_url:
            thumbnail_url = "https://placehold.jp/333333/cccccc/130x100.png?text=No%20Image"
            
        embed = discord.Embed(title=title, url=watch_url, color=discord.Color.blue())
        embed.set_author(name="▶️ 現在再生中の曲")
        embed.set_thumbnail(url=thumbnail_url)
        
        if duration > 0:
            elapsed = duration - remaining
            percent = min(10, max(0, int((elapsed / duration) * 10)))
            bar = "▓" * percent + "░" * (10 - percent)
            
            def format_time(seconds):
                m = seconds // 60
                s = seconds % 60
                return f"{m:02d}:{s:02d}"
                
            embed.description = f"`{bar}` ({format_time(elapsed)} / {format_time(duration)})\n残り時間: 約 {format_time(remaining)}"
        else:
            embed.description = f"動画ID: {video_id}"
            
        embed.set_footer(text="Powered by NUCOSen")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to fetch nowplaying: {e}")
        await interaction.response.send_message("⚠️ 現在の再生情報の取得に失敗しました。", ephemeral=True)


@tree.command(name="queue", description="待機中のキュー一覧を表示します")
async def queue_cmd(interaction: discord.Interaction):
    db_uri = config("REQBOT_DB_URI", cast=str)
    if db_uri.endswith("/requests"):
        queue_uri = db_uri[:-9] + "/queue"
    else:
        queue_uri = db_uri + "/queue"
        
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
    
    try:
        import asyncio
        from requests import get
        query = '?h={\"\$orderby\": {\"priority\": -1, \"_id\": 1}}&max=10'
        resp = await asyncio.to_thread(get, url=queue_uri + query, headers=headers, timeout=10)
        resp.raise_for_status()
        queues = resp.json()
        
        if not queues:
            await interaction.response.send_message("🎵 現在キューは空です。リクエストを送ってみましょう！")
            return
            
        embed = discord.Embed(title="📋 待機中のキュー一覧", color=discord.Color.green())
        
        description_lines = []
        for index, item in enumerate(queues):
            video_id = item["videoId"]
            priority_str = "⭐ [優先] " if item.get("priority") else ""
            description_lines.append(f"**{index + 1}.** {priority_str}`{video_id}` - [動画リンク](https://www.nicovideo.jp/watch/{video_id})")
            
        embed.description = "\n".join(description_lines)
        embed.set_footer(text=f"合計 {len(queues)} 件の待機曲があります。")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to fetch queue: {e}")
        await interaction.response.send_message("⚠️ キュー情報の取得に失敗しました。", ephemeral=True)
