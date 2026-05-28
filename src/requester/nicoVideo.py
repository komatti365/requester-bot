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
    lengthSeconds: Optional[int] = None
    tags: Optional[list[str]] = None
    genre: Optional[str] = None

    def __post_init__(self):
        matched = self.idPattern.search(self.id)
        self.id = matched.group() if matched else "sm0"

        infoXml = get(self.infoApiPrefix + self.id, timeout=60)
        infoXml.raise_for_status()
        thumbInfoTree = ET.fromstring(infoXml.content)

        self.isExists = bool(thumbInfoTree.get("status") == "ok")
        if not self.isExists:
            return

        # NOTE - thumbInfoTree.find(x) MUST NOT be None.
        self.title, self.watchUrl, self.thumbnailUrl, length_text = \
            [
                thumbInfoTree.find(path).text for path in  # type: ignore \
                (".//title", ".//watch_url", ".//thumbnail_url", ".//length")
            ]
            
        genre_elem = thumbInfoTree.find(".//genre")
        self.genre = genre_elem.text if genre_elem is not None else None
            
        if length_text:
            parts = length_text.split(":")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                self.lengthSeconds = int(parts[0]) * 60 + int(parts[1])
                
        self.tags = [tag.text for tag in thumbInfoTree.findall(".//tag") if tag.text]

    def __str__(self) -> str:
        return self.id
