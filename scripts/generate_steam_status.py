#!/usr/bin/env python3
"""Generate a Steam now-playing PNG without showing the profile avatar."""

from __future__ import annotations

import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

STEAM_ID = os.environ.get("STEAM_ID", "76561198355636398")
OUTPUT = Path(os.environ.get("OUTPUT_PATH", "assets/steam-now-playing.png"))

STATUS_COLORS = {
    "online": "#57cbde",
    "in-game": "#90ba3c",
    "busy": "#c7a008",
    "away": "#f0ad4e",
    "snooze": "#f0ad4e",
    "offline": "#898989",
    "looking to trade": "#c7a008",
    "looking to play": "#57cbde",
}

FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
)


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    paths = FONT_CANDIDATES if bold else reversed(FONT_CANDIDATES)
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def fetch_profile_xml(steam_id: str) -> ET.Element:
    url = f"https://steamcommunity.com/profiles/{steam_id}/?xml=1"
    request = urllib.request.Request(url, headers={"User-Agent": "basit3000-profile-readme/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return ET.fromstring(response.read())


def text(element: ET.Element, tag: str, default: str = "") -> str:
    node = element.find(tag)
    if node is None or node.text is None:
        return default
    return node.text.strip()


def extract_in_game_name(state_message: str, online_state: str) -> str:
    if online_state != "in-game":
        return ""

    plain = re.sub(r"<br\s*/?>", "\n", state_message, flags=re.IGNORECASE)
    plain = re.sub(r"<[^>]+>", "", plain)
    parts = [part.strip() for part in plain.split("\n") if part.strip()]

    for part in parts:
        if part.lower() not in {"in-game", "in game"}:
            return part

    return ""


def status_line(profile: ET.Element) -> tuple[str, str, str]:
    online_state = text(profile, "onlineState", "offline").lower()
    game_name = text(profile, "gameName") or text(profile, "gameExtraInfo")
    in_game_info = text(profile, "inGameInfo")
    state_message = text(profile, "stateMessage", online_state.title())

    if not game_name:
        game_name = extract_in_game_name(state_message, online_state)

    if game_name or in_game_info or online_state == "in-game":
        title = "In-Game"
        detail = game_name or in_game_info or "Playing now"
        color = STATUS_COLORS["in-game"]
    else:
        title = "Steam"
        plain_status = re.sub(r"<[^>]+>", " ", state_message).strip()
        detail = plain_status or online_state.title()
        color = STATUS_COLORS.get(online_state, STATUS_COLORS["offline"])

    return title, detail, color


def draw_steam_icon(draw: ImageDraw.ImageDraw) -> None:
    cx, cy, r = 42, 60, 24
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill="#1b2838", outline="#66c0f4", width=2)
    draw.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), fill="#c7d5e0")
    draw.ellipse((46, 49, 52, 55), fill="#66c0f4")
    draw.ellipse((54, 57, 60, 63), fill="#66c0f4")


def build_png(title: str, detail: str, accent: str, output: Path) -> None:
    if len(detail) > 34:
        detail = detail[:31] + "..."

    width, height = 340, 112
    image = Image.new("RGB", (width, height), "#171a21")
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=10, fill="#1b2838", outline="#2a475e")
    draw_steam_icon(draw)

    title_font = load_font(13, bold=True)
    detail_font = load_font(20, bold=True)
    sub_font = load_font(11)
    brand_font = load_font(10, bold=True)

    draw.text((84, 26), title, fill="#66c0f4", font=title_font)
    draw.text((84, 46), detail, fill=accent, font=detail_font)
    draw.text((84, 78), "Now playing on Steam", fill="#8f98a0", font=sub_font)
    draw.text((268, 12), "STEAM", fill="#5c6978", font=brand_font)

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG")


def main() -> int:
    try:
        profile = fetch_profile_xml(STEAM_ID)
    except (urllib.error.URLError, ET.ParseError) as exc:
        print(f"Failed to fetch Steam profile: {exc}", file=sys.stderr)
        return 1

    title, detail, accent = status_line(profile)
    build_png(title, detail, accent, OUTPUT)
    print(f"Wrote {OUTPUT} ({title}: {detail})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
