import logging
from requester import bot
from os import getcwd
from decouple import AutoConfig
import sys

def execute():
    readyLogging()
    checkConfig()
    bot.startDiscordBot()


def checkConfig():
    import os
    from decouple import Config, RepositoryEnv
    
    _env_path = os.environ.get("REQBOT_ENV_PATH")
    if _env_path:
        config = Config(RepositoryEnv(_env_path))
    else:
        config = AutoConfig(os.getcwd())
    
    configNames = (
        "REQBOT_DB_URI",
        "REQBOT_DB_KEY",
        "REQBOT_TOKEN",
        "REQBOT_WATCH_CHANNEL"
    )
    configs = []
    for configName in configNames:
        val = config(configName, default=None)
        if configName == "REQBOT_DB_KEY" and not val and os.environ.get("REQBOT_DB_KEY_FILE"):
            val = "provided_by_file"
        configs.append(val)
        
    if None in configs:
        logger = logging.getLogger(__name__)
        logger.critical("初期設定が未完了です")
        logger.critical("See also: https://bit.ly/3Gpu9TU")
        sys.exit("Error code : C00")


def readyLogging():
    # ログハンドラの設定
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "{asctime} [{levelname}] {message}", style="{")
    stream_handler.setFormatter(formatter)

    # ロガーにハンドラを追加
    logging.root.addHandler(stream_handler)
    logging.root.setLevel(logging.DEBUG)


if __name__ == "__main__":
    execute()
