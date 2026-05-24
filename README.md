![repo_icon](https://github.com/nucosen/requester-bot/assets/93378833/fc15aea6-1155-477a-ba4d-b7cf0adfe8b4)

# NUCOSen REQUESTER for Discord - NRD

> [NUCOSen Broadcast](https://github.com/nucosen/broadcast)を前提としたプログラムです

NUCOSenエコシステムの、リクエスト受付窓口を担うDiscord Botです。
Discordの機能と組み合わせることで、リクエスト権の与奪やマネタイズが非常に容易になります。

## Installing / Getting started

このインストール方式は、Python3.10以上およびpipが導入されていることが前提です。

```shell
pip install https://github.com/nucosen/requester-bot/releases/latest/download/requester-latest.tar.gz
```

初期設定後、`requester`コマンドで起動します。

```shell
> requester
[2023-04-05 06:07:08] [INFO    ] discord.client: logging in using static token
2023-04-05 06:07:08,901 [INFO] logging in using static token
[2023-04-05 06:07:08] [INFO    ] discord.gateway: Shard ID None has connected to Gateway (Session ID: 1234567890abcdef1234567890abcdef).
2023-04-05 06:07:08,901 [INFO] Shard ID None has connected to Gateway (Session ID: 1234567890abcdef1234567890abcdef).
2023-04-05 06:07:08,901 [INFO] We have logged in as Requester#1234
2023-04-05 06:07:08,901 [INFO]
2023-04-05 06:07:08,901 [INFO]     _  _ _  _ ____ ____ ____ ____ _  _
2023-04-05 06:07:08,901 [INFO]     |\ | |  | |    |  | [__  |___ |\ |
2023-04-05 06:07:08,901 [INFO]     | \| |__| |___ |__| ___] |___ | \|
2023-04-05 06:07:08,901 [INFO]     ____ ____ ____    ___  ____ ___
2023-04-05 06:07:08,901 [INFO]     |__/ |___ |  | __ |__] |  |  |
2023-04-05 06:07:08,901 [INFO]     |  \ |___ |_\|    |__] |__|  |
2023-04-05 06:07:08,901 [INFO]
```

### 初期設定

Discordボットのトークン、および監視先チャンネルのチャンネルIDが必要です。

パッケージのインストール先・カレントディレクトリのいずれかに`.env`ファイルを作成するか、システムの環境変数を設定します。
また、環境変数 `REQBOT_ENV_PATH` にファイルのパスを設定することで、任意の場所にある `.env` ファイルを読み込むことも可能です。

両方存在する場合は、環境変数を優先します。

.envのサンプル：

```env
# リクエストデータベースのエンドポイント
REQBOT_DB_URI=https://example.restdb.io/rest/example
# リクエストデータベースのAPI鍵
REQBOT_DB_KEY=1234567890abcdef1234567890abcdef12345
# またはマウントファイルから読み込む場合:
# REQBOT_DB_KEY_FILE=/secrets/db_key.txt
# Botのトークン。パブリックキーやアプリケーションIDではありません。
REQBOT_TOKEN=ABCDEFGHIJKLMNOPQRSTUVWXYZ.123456.abcdefghijklmnopqrstuvwxyz1234567890_0
# 監視先DiscordチャンネルのID
REQBOT_WATCH_CHANNEL=1012345678901234567
```

## 開発環境の構築

独自の拡張を導入する場合や、プロジェクトへの貢献のためにプロジェクトをクローンする場合は以下の手順に従います。

Pipenvの導入を強く推奨します。以下の手順はPipenvの導入を前提としています。

```shell
git clone https://github.com/nucosen/requester-bot.git
cd requester-bot
pipenv install
```

### パッケージング

setup.pyを導入しています。プログラムをパッケージ形式にしたい場合は、作業前に`setup.py`のバージョン番号を更新してください。

オリジナルとの区別のため、パッケージ名を変えずに拡張したものは元となったバージョンの後ろにCustomを意味する`c`をつけたものを使用すべきです。

例えば、`1.2.3`を元にした拡張版は：`1.2.3c1` `1.2.3c1.0.1` `1.2.3c30123.456` などを使用できます。

```shell
pipenv shell
python setup.py sdist
```

## 機能概要

* Discordの特定チャンネルに投げられたURLや動画IDを検知し、動画の存在確認ののちリクエストデータベースにPOSTします。
* コマンド指定が不要なため、例えば動画アプリから「共有」→「Discord」→該当するチャンネルへ送信 の操作のみで簡単にリクエストが完了します。
* リクエスト成功時にサムネイル・タイトル・動画へのリンクを出力するため、どのような動画がリクエストされたかがわかります。

## 追加設定

`.env`ファイル、または環境変数へ以下の値を設定することで設定を変更することができます。これらは任意です。

> （追加設定は現在のところ実装されていません。必須の設定は「初期設定」を参照してください）

## フィードバック

Requester-botに関する質問やバグ報告、提案などのフィードバックはいつでも歓迎します。ただし、リリース前のバージョンやカスタムしたフォーク先などのバージョンはサポートできません。

**その前に：**[開発者ドキュメント](https://github.com/nucosen/requester-bot/docs/index.md)を読んだほうが早く解決するかもしれません。エラーメッセージの一覧やよくある質問などをまとめています。負担軽減にご協力ください。

- バグ報告・新機能の提案：[Issueページ](https://github.com/nucosen/requester-bot/issues)
- ご支援：[Ofuse](https://ofuse.me/sittingcat)
- その他、質問・感想など：[開発者Twitter](https://twitter.com/cuYkqv)

OfuseにIssue番号を記載していただければ、優先的に実装・対応いたします。

（支援の有無に関わらず、全てのIssueに記載された機能等の実装をお約束するものではございません。）

## コントリビューティング

このリポジトリへのコントリビューションを歓迎します。以下の文書を参照してください。

- [行動規範](CODE_OF_CONDUCT.md)
- [セキュリティポリシー](SECURITY.md)
- [コントリビューションガイドライン](CONTRIBUTING.md)

## ライセンス

このプログラムはMITライセンスのもとで提供されています。詳細については、[LICENSEドキュメント](LICENSE)（英文）をご確認ください。
