#!/usr/bin/env python3
"""Generate a Steam now-playing PNG card for the profile README.

The card is 340x120 with transparent rounded corners so it sits flush next to
the site's Spotify widget (same size) in both GitHub colour modes. Steam's
community XML endpoint rate-limits shared runner IPs, so fetches are retried
and, if Steam still won't answer, the previous image is left untouched instead
of failing the workflow.
"""

from __future__ import annotations

import os
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

STEAM_ID = os.environ.get("STEAM_ID", "76561198355636398")
OUTPUT = Path(os.environ.get("OUTPUT_PATH", "assets/steam-now-playing.png"))

WIDTH, HEIGHT = 340, 120
SCALE = 2  # supersample, then downscale for smooth edges
TEXT_X = 104
TEXT_RIGHT_PAD = 16

BG = "#1b2838"
BORDER = "#2a475e"
HEADLINE = "#ffffff"
MUTED = "#8f98a0"
STEAM_BLUE = "#66c0f4"
IN_GAME_GREEN = "#90ba3c"
AWAY_AMBER = "#f0ad4e"
OFFLINE_GREY = "#7a8791"

FONT_CANDIDATES_BOLD = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
)
FONT_CANDIDATES_REGULAR = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
)

RETRY_DELAYS = (0, 6, 15)  # seconds before each attempt


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES_BOLD if bold else FONT_CANDIDATES_REGULAR:
        if Path(path).exists():
            return ImageFont.truetype(path, size * SCALE)
    return ImageFont.load_default(size * SCALE)


def fetch_profile_xml(steam_id: str) -> ET.Element:
    url = f"https://steamcommunity.com/profiles/{steam_id}/?xml=1"
    request = urllib.request.Request(url, headers={"User-Agent": "basit3000-profile-readme/1.1"})
    last_error: Exception | None = None
    for attempt, delay in enumerate(RETRY_DELAYS, start=1):
        if delay:
            time.sleep(delay)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return ET.fromstring(response.read())
        except (urllib.error.URLError, ET.ParseError, TimeoutError) as exc:
            last_error = exc
            print(f"Attempt {attempt}/{len(RETRY_DELAYS)} failed: {exc}", file=sys.stderr)
    assert last_error is not None
    raise last_error


def text(element: ET.Element, tag: str, default: str = "") -> str:
    node = element.find(tag)
    if node is None or node.text is None:
        return default
    return node.text.strip()


def strip_html(value: str) -> list[str]:
    plain = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    plain = re.sub(r"<[^>]+>", "", plain)
    return [part.strip() for part in plain.split("\n") if part.strip()]


def extract_in_game_name(state_message: str) -> str:
    for part in strip_html(state_message):
        if part.lower() not in {"in-game", "in game"}:
            return part
    return ""


def status_line(profile: ET.Element) -> tuple[str, str, str, str]:
    """Return (eyebrow, headline, caption, accent) for the card."""
    online_state = text(profile, "onlineState", "offline").lower()
    state_message = text(profile, "stateMessage", online_state.title())
    game_name = (
        text(profile, "gameName")
        or text(profile, "gameExtraInfo")
        or text(profile, "inGameInfo/gameName")
        or (extract_in_game_name(state_message) if online_state == "in-game" else "")
    )

    if game_name or online_state == "in-game":
        return "IN-GAME", game_name or "Playing now", "Now playing on Steam", IN_GAME_GREEN

    plain_status = " ".join(strip_html(state_message)) or online_state.title()
    lowered = plain_status.lower()

    if online_state == "online":
        if any(word in lowered for word in ("away", "snooze", "busy")):
            return "STEAM", plain_status.title(), "Idle on Steam", AWAY_AMBER
        return "STEAM", "Online", "Online, not in a game", STEAM_BLUE

    if lowered.startswith("last online"):
        # "Last Online 3 hrs, 12 mins ago" -> "Last online 3 hrs, 12 mins ago"
        return "STEAM", "Offline", "Last online" + plain_status[len("Last Online"):], OFFLINE_GREY
    return "STEAM", "Offline", "Not playing right now", OFFLINE_GREY


def fit_text(value: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width_px: int) -> str:
    """Trim `value` with an ellipsis so its rendered width fits `max_width_px`."""
    limit = max_width_px * SCALE
    if font.getlength(value) <= limit:
        return value
    ellipsis = "\u2026"
    trimmed = value
    while trimmed and font.getlength(trimmed.rstrip() + ellipsis) > limit:
        trimmed = trimmed[:-1]
    return trimmed.rstrip() + ellipsis


def s(*values: float) -> tuple[int, ...]:
    return tuple(int(round(v * SCALE)) for v in values)


def draw_steam_mark(draw: ImageDraw.ImageDraw, accent: str) -> None:
    cx, cy, r = 56, 60, 26
    draw.ellipse(s(cx - r, cy - r, cx + r, cy + r), fill=BORDER, outline=accent, width=2 * SCALE)
    # Steam logo approximation: big ring top-right, small ring bottom-left, joined by a bar.
    big = (cx + 6, cy - 7, 9)
    small = (cx - 8, cy + 8, 5)
    draw.line(s(small[0], small[1], big[0], big[1]), fill="#c7d5e0", width=5 * SCALE)
    for x, y, rad in (big, small):
        draw.ellipse(s(x - rad, y - rad, x + rad, y + rad), fill="#c7d5e0")
        inner = rad - 3
        draw.ellipse(s(x - inner, y - inner, x + inner, y + inner), fill=BORDER)


def build_png(eyebrow: str, headline: str, caption: str, accent: str, output: Path) -> None:
    image = Image.new("RGBA", (WIDTH * SCALE, HEIGHT * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(
        s(0.5, 0.5, WIDTH - 0.5, HEIGHT - 0.5),
        radius=12 * SCALE,
        fill=BG,
        outline=BORDER,
        width=SCALE,
    )
    draw_steam_mark(draw, accent)

    eyebrow_font = load_font(11, bold=True)
    headline_font = load_font(18, bold=True)
    caption_font = load_font(13)

    max_text_width = WIDTH - TEXT_X - TEXT_RIGHT_PAD
    headline = fit_text(headline, headline_font, max_text_width)
    caption = fit_text(caption, caption_font, max_text_width)

    # Status dot + eyebrow label
    dot_r = 3
    draw.ellipse(s(TEXT_X, 31 - dot_r, TEXT_X + 2 * dot_r, 31 + dot_r), fill=accent)
    draw.text(s(TEXT_X + 12, 25), eyebrow, fill=accent, font=eyebrow_font)
    draw.text(s(TEXT_X, 42), headline, fill=HEADLINE, font=headline_font)
    draw.text(s(TEXT_X, 74), caption, fill=MUTED, font=caption_font)

    image = image.resize((WIDTH, HEIGHT), Image.LANCZOS)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=True)


def main() -> int:
    try:
        profile = fetch_profile_xml(STEAM_ID)
    except (urllib.error.URLError, ET.ParseError, TimeoutError) as exc:
        if OUTPUT.exists():
            print(f"::warning::Steam unreachable ({exc}); keeping previous {OUTPUT}")
            return 0
        print(f"::warning::Steam unreachable ({exc}); writing placeholder card")
        build_png("STEAM", "Unavailable", "Couldn't reach Steam", OFFLINE_GREY, OUTPUT)
        return 0

    eyebrow, headline, caption, accent = status_line(profile)
    build_png(eyebrow, headline, caption, accent, OUTPUT)
    print(f"Wrote {OUTPUT} ({eyebrow}: {headline} - {caption})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
