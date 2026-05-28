# -*- coding: utf-8 -*-
import sys
from unittest.mock import MagicMock

# discordモジュールをモックしてインポートエラーを回避する
sys.modules["discord"] = MagicMock()

try:
    sys.path.append("~/../src")
finally:
    from requester.bot import isValidRequest

class StubNicoVideo:
    def __init__(self, id, tags, genre="音楽・サウンド", lengthSeconds=100, isExists=True, title="Test", watchUrl="https://nico.ms/sm1"):
        self.id = id
        self.tags = tags
        self.genre = genre
        self.lengthSeconds = lengthSeconds
        self.isExists = isExists
        self.title = title
        self.watchUrl = watchUrl

def test_isValidRequest_ng_tags_exact():
    video = StubNicoVideo("sm1", ["VOCALOID", "歌ってみた"])
    
    # 完全一致NGタグがヒットする場合
    settings = {"NG_TAGS_EXACT": "VOCALOID,音MAD"}
    is_valid, reason = isValidRequest(video, settings)
    assert not is_valid
    assert "NGタグが含まれているため" in reason

    # 完全一致NGタグがヒットしない場合
    settings = {"NG_TAGS_EXACT": "Vocaloid,音MAD"}  # 大文字小文字が違う
    is_valid, reason = isValidRequest(video, settings)
    assert is_valid

def test_isValidRequest_ng_tags_partial():
    video = StubNicoVideo("sm1", ["人力VOCALOID", "歌ってみた"])
    
    # 部分一致NGタグがヒットする場合
    settings = {"NG_TAGS": "VOCALOID,音MAD"}
    is_valid, reason = isValidRequest(video, settings)
    assert not is_valid
    assert "NGタグ「VOCALOID」が含まれているため" in reason

    # 部分一致NGタグがヒットしない場合
    settings = {"NG_TAGS": "東方,音MAD"}
    is_valid, reason = isValidRequest(video, settings)
    assert is_valid

def test_isValidRequest_req_tags_exact():
    video = StubNicoVideo("sm1", ["VOCALOID", "初音ミク"])
    
    # 完全一致必須タグがある場合 (含む)
    settings = {"REQTAGS_EXACT": "VOCALOID,CeVIO"}
    is_valid, reason = isValidRequest(video, settings)
    assert is_valid

    # 完全一致必須タグがある場合 (含まない)
    settings = {"REQTAGS_EXACT": "Vocaloid,CeVIO"} # 完全一致しない
    is_valid, reason = isValidRequest(video, settings)
    assert not is_valid
    assert "リクエストに必要なタグ" in reason

def test_isValidRequest_req_tags_partial():
    video = StubNicoVideo("sm1", ["初音ミクオリジナル曲", "歌ってみた"])
    
    # 部分一致必須タグがある場合 (含む)
    settings = {"REQTAGS": "初音ミク,CeVIO"}
    is_valid, reason = isValidRequest(video, settings)
    assert is_valid

    # 部分一致必須タグがある場合 (含まない)
    settings = {"REQTAGS": "鏡音リン,CeVIO"}
    is_valid, reason = isValidRequest(video, settings)
    assert not is_valid
    assert "リクエストに必要なタグ" in reason

def test_isValidRequest_genre():
    # 許可ジャンルに含まれる場合
    video = StubNicoVideo("sm1", ["VOCALOID"], genre="音楽・サウンド")
    settings = {"GENRE_TAGS": "音楽・サウンド,ゲーム"}
    is_valid, reason = isValidRequest(video, settings)
    assert is_valid

    # 許可ジャンルに含まれる場合 (部分一致)
    video = StubNicoVideo("sm1", ["VOCALOID"], genre="音楽・サウンド")
    settings = {"GENRE_TAGS": "音楽,ゲーム"}
    is_valid, reason = isValidRequest(video, settings)
    assert is_valid

    # 許可ジャンルに含まれない場合
    video = StubNicoVideo("sm1", ["VOCALOID"], genre="ゲーム")
    settings = {"GENRE_TAGS": "音楽・サウンド,エンタメ"}
    is_valid, reason = isValidRequest(video, settings)
    assert not is_valid
    assert "ジャンル（ゲーム）はリクエスト対象外です" in reason

    # 動画のジャンルが None の場合
    video = StubNicoVideo("sm1", ["VOCALOID"], genre=None)
    settings = {"GENRE_TAGS": "音楽・サウンド,ゲーム"}
    is_valid, reason = isValidRequest(video, settings)
    assert not is_valid
    assert "ジャンル（（なし））はリクエスト対象外です" in reason
