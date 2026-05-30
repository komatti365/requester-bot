# NOTE : This program requires the 'message_content' intent.

import discord
import logging
import asyncio
from decouple import AutoConfig, Config, RepositoryEnv, UndefinedValueError
from requests import get, post
from .nicoVideo import NicoVideo
import os
import time
from discord.ext import tasks

logger = logging.getLogger(__name__)


_env_path = os.environ.get("REQBOT_ENV_PATH")
if _env_path:
    config = Config(RepositoryEnv(_env_path))
else:
    config = AutoConfig(os.getcwd())

intents = discord.Intents.default()
intents.message_content = True

client = discord.Bot(intents=intents)


# SECTION - イベント定義


@client.event
async def on_ready():
    logger.info(f'We have logged in as {client.user}')
    logo = r"""
    _  _ _  _ ____ ____ ____ ____ _  _
    |\ | |  | |    |  | [__  |___ |\ |
    | \| |__| |___ |__| ___] |___ | \|
    ____ ____ ____    ___  ____ ___
    |__/ |___ |  | __ |__] |  |  |
    |  \ |___ |_\|    |__] |__|  |
    """.splitlines()

    for line in logo:
        logger.info(line)

    if not update_status_loop.is_running():
        update_status_loop.start()


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
            
        # DBから設定を取得し、条件を検証する
        settings = getSettings()
        is_valid, reason = isValidRequest(video, settings)
        if not is_valid:
            # 条件に合わない場合は理由をリプライして終了
            await message.reply(f"⚠️ リクエストを受け付けられませんでした。\n理由: {reason}")
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

def getSettings() -> dict:
    """DBのAPIから設定を取得する"""
    try:
        settings_uri = config("REQBOT_SETTINGS_URI", default="")
        if not settings_uri:
            settings_uri = config("SETTINGS_URL", default="")
            
        if not settings_uri:
            db_uri = config("REQBOT_DB_URI", cast=str)
            if db_uri.endswith("/requests"):
                settings_uri = db_uri[:-9] + "/config"
            else:
                settings_uri = db_uri + "/config"
    except UndefinedValueError:
        return {}
        
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
        resp = get(url=settings_uri, headers=headers, timeout=10)
        resp.raise_for_status()
        
        documents = resp.json()
        settings = {}
        # JSONの構造が [{"key": "HOGE", "value": "FUGA"}] のような形を想定
        if isinstance(documents, list):
            for doc in documents:
                if "key" in doc and "value" in doc and doc["value"] is not None:
                    settings[doc["key"]] = str(doc["value"])
        return settings
    except Exception as e:
        logger.error(f"DBからの設定取得に失敗しました: {e}")
        return {}

def isValidRequest(video: NicoVideo, settings: dict) -> tuple[bool, str]:
    """リクエストされた動画が条件を満たしているか検証する"""
    def get_setting(key: str, default_val: str = "") -> str:
        # 設定エンドポイント(settings)からの最新の設定を最優先し、無ければ環境変数(config)から取得する
        val = settings.get(key)
        if val is not None and val != "":
            return str(val)
        try:
            return str(config(key, default=default_val))
        except Exception:
            return default_val

    try:
        min_duration = int(get_setting("MIN_ALLOWABLE_DURATION", "45"))
    except ValueError:
        min_duration = 45

    try:
        max_duration = int(get_setting("MAX_ALLOWABLE_DURATION", "600"))
    except ValueError:
        max_duration = 600
    
    length_seconds = getattr(video, "lengthSeconds", None)
    if length_seconds is not None:
        if length_seconds < min_duration:
            return False, f"動画が短すぎます（{min_duration}秒以上が必要です）"
        if length_seconds > max_duration:
            return False, f"動画が長すぎます（{max_duration}秒以下が必要です）"
            
    ng_videos = set(filter(None, get_setting("NG_VIDEO_IDS").split(",")))
    if video.id in ng_videos:
        return False, "この動画はリクエストが禁止されています。"
        
    video_tags_attr = getattr(video, "tags", None)
    video_tags = [t.strip() for t in video_tags_attr] if video_tags_attr else []
    video_tags_set = set(video_tags)
    
    # 1. NG_TAGS_EXACT (完全一致NG)
    ng_tags_exact = set(filter(None, [t.strip() for t in get_setting("NG_TAGS_EXACT").split(",")]))
    if len(ng_tags_exact & video_tags_set) > 0:
        return False, "NGタグが含まれているためリクエストできません。"
        
    # 2. NG_TAGS (部分一致NG)
    ng_tags = [t.strip() for t in get_setting("NG_TAGS").split(",") if t.strip()]
    for ng_tag in ng_tags:
        for tag in video_tags:
            if ng_tag in tag:
                return False, f"NGタグ「{ng_tag}」が含まれているためリクエストできません。"

    # 3. REQTAGS_EXACT (完全一致必須)
    req_tags_exact_str = get_setting("REQTAGS_EXACT")
    if req_tags_exact_str:
        req_tags_exact = set(filter(None, [t.strip() for t in req_tags_exact_str.split(",")]))
        if req_tags_exact and not (req_tags_exact & video_tags_set):
            return False, f"リクエストに必要なタグ（{req_tags_exact_str}）が含まれていません。"

    # 4. REQTAGS (部分一致必須)
    req_tags_str = get_setting("REQTAGS")
    if req_tags_str:
        req_tags = [t.strip() for t in req_tags_str.split(",") if t.strip()]
        if req_tags:
            matched = False
            for req_tag in req_tags:
                for tag in video_tags:
                    if req_tag in tag:
                        matched = True
                        break
                if matched:
                    break
            if not matched:
                return False, f"リクエストに必要なタグ（{req_tags_str}）が含まれていません。"
            
    # 5. ジャンルチェック (GENRE_TAGS)
    genre_tags_str = get_setting("GENRE_TAGS")
    if genre_tags_str:
        allowed_genres = [g.strip() for g in genre_tags_str.split(",") if g.strip()]
        if allowed_genres:
            genre_matched = False
            video_genre = getattr(video, "genre", None)
            if video_genre:
                video_genre_clean = video_genre.strip()
                for allowed_genre in allowed_genres:
                    if allowed_genre in video_genre_clean or video_genre_clean in allowed_genre:
                        genre_matched = True
                        break
            if not genre_matched:
                actual_genre = video_genre or "（なし）"
                return False, f"この動画のジャンル（{actual_genre}）はリクエスト対象外です。"
            
    return True, ""

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
        json={
            "videoId": str(item),
            "title": item.title,
            "thumbnailUrl": item.thumbnailUrl
        }, headers=headers,
        timeout=60
    )
    resp.raise_for_status()


async def fetch_nowplaying() -> dict | None:
    """現在再生中の動画情報をDBのAPIから取得する"""
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
        from requests import get as sync_get
        resp = await asyncio.to_thread(sync_get, url=nowplaying_uri, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        item = None
        if isinstance(data, list) and len(data) > 0:
            first_element = data[0]
            if isinstance(first_element, dict):
                item = first_element
        elif isinstance(data, dict) and data:
            item = data
        return item
    except Exception as e:
        logger.error(f"Failed to fetch nowplaying: {e}")
        return None


_last_video_id = None


@tasks.loop(seconds=15)
async def update_status_loop():
    """15秒ごとに現在再生中の曲を取得し、Botのステータス（アクティビティ）を更新する"""
    global _last_video_id
    try:
        item = await fetch_nowplaying()
        if not item or not item.get("videoId"):
            # 再生中でなければステータスをクリア
            if _last_video_id is not None:
                await client.change_presence(activity=None)
                _last_video_id = None
            return

        video_id = item["videoId"]
        if video_id == _last_video_id:
            # 同じ曲が流れている間はステータス更新をスキップ（レートリミット対策）
            return

        title = item.get("title", "（タイトル不明）")
        duration = item.get("duration", 0)
        remaining = item.get("remainingTime", 0)

        if duration > 0:
            now = time.time()
            elapsed = duration - remaining
            start_time = now - elapsed
            end_time = now + remaining

            activity = discord.Activity(
                type=discord.ActivityType.listening,
                name=title,
                timestamps={"start": int(start_time), "end": int(end_time)}
            )
        else:
            activity = discord.Activity(
                type=discord.ActivityType.listening,
                name=title
            )

        await client.change_presence(activity=activity)
        _last_video_id = video_id
    except Exception as e:
        logger.error(f"Failed to update status in loop: {e}")


# SECTION - スラッシュコマンド定義

@client.slash_command(name="nowplaying", description="現在放送中の動画を表示します")
async def nowplaying_cmd(ctx: discord.ApplicationContext):
    try:
        item = await fetch_nowplaying()
        if not item or not item.get("videoId"):
            await ctx.respond("🎵 現在放送中の曲はありません。", ephemeral=True)
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
        await ctx.respond(embed=embed)
    except Exception as e:
        logger.error(f"Failed to show nowplaying: {e}")
        await ctx.respond("⚠️ 現在の再生情報の取得に失敗しました。", ephemeral=True)


@client.slash_command(name="queue", description="待機中のキュー一覧を表示します")
async def queue_cmd(ctx: discord.ApplicationContext):
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
        from requests import get
        query = '?h={\"\$orderby\": {\"priority\": -1, \"_id\": 1}}&max=10'
        resp = await asyncio.to_thread(get, url=queue_uri + query, headers=headers, timeout=10)
        resp.raise_for_status()
        queues = resp.json()
        
        if not queues:
            await ctx.respond("🎵 現在キューは空です。リクエストを送ってみましょう！")
            return
            
        embed = discord.Embed(title="📋 待機中のキュー一覧", color=discord.Color.green())
        
        description_lines = []
        for index, item in enumerate(queues):
            video_id = item["videoId"]
            title = item.get("title", video_id)
            if len(title) > 40:
                title = title[:40] + "..."
            priority_str = "⭐ [優先] " if item.get("priority") else ""
            description_lines.append(f"**{index + 1}.** {priority_str}[{title}](https://www.nicovideo.jp/watch/{video_id})")
            
        embed.description = "\n".join(description_lines)
        embed.set_footer(text=f"合計 {len(queues)} 件の待機曲があります。")
        await ctx.respond(embed=embed)
    except Exception as e:
        logger.error(f"Failed to fetch queue: {e}")
        await ctx.respond("⚠️ キュー情報の取得に失敗しました。", ephemeral=True)
