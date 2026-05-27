import re
from typing import Optional
from requests import get
import defusedxml.ElementTree as ET
from dataclasses import dataclass


@dataclass
class NicoVideo:
    id: str
    idPattern: re.Pattern[str] = re.compile(r"[sn]m[0-9]+")
    errorVideoId: Optional[str] = "sm0"

    infoApiPrefix: str = "https://ext.nicovideo.jp/api/getthumbinfo/"
    isExists: Optional[bool] = None
    title: Optional[str] = None
    watchUrl: Optional[str] = None
    thumbnailUrl: Optional[str] = None

    def __post_init__(self):
        matched = self.idPattern.search(self.id)
        self.id = matched.group() if matched else "sm0"

        infoXml = get(self.infoApiPrefix + self.id, timeout=60)
        infoXml.raise_for_status()
        thumbInfoTree = ET.fromstring(infoXml.text)

        self.isExists = bool(thumbInfoTree.get("status") == "ok")
        if not self.isExists:
            return

        # NOTE - thumbInfoTree.find(x) MUST NOT be None.
        self.title, self.watchUrl, self.thumbnailUrl = \
            [
                thumbInfoTree.find(path).text for path in  # type: ignore \
                (".//title", ".//watch_url", ".//thumbnail_url")
            ]

    def __str__(self) -> str:
        return self.id
