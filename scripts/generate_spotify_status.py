#!/usr/bin/env python3
"""Generate a Spotify now-playing PNG for the GitHub profile README."""

from __future__ import annotations

import html
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SPOTIFY_UID = os.environ.get("SPOTIFY_UID", "ic9zxmbzknyeuiza6yh988k8n")
OUTPUT = Path(os.environ.get("OUTPUT_PATH", "assets/spotify-now-playing.png"))

SPOTIFY_VIEW_URL = (
    "https://spotify-github-profile.kittinanx.com/api/view"
    f"?uid={SPOTIFY_UID}&cover_image=false&theme=compact"
    "&show_offline=true&background_color=121212"
)

FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
)

EQ_HEIGHTS = (
    5, 9, 12, 8, 14, 10, 6, 13, 7, 11, 9, 14, 6, 10, 12, 8, 13, 7, 11, 9,
    14, 6, 10, 12, 8, 13, 7, 11, 9, 14, 6, 10, 12, 8, 13, 7, 11, 9, 14, 6,
)


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    paths = FONT_CANDIDATES if bold else reversed(FONT_CANDIDATES)
    for path in paths:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def fetch_svg() -> str:
    request = urllib.request.Request(
        SPOTIFY_VIEW_URL,
        headers={"User-Agent": "basit3000-profile-readme/1.0"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_track(svg: str) -> tuple[str, str, bool]:
    artist_match = re.search(r'class="artist"[^>]*>([^<]+)<', svg, re.IGNORECASE)
    song_match = re.search(r'class="song"[^>]*>([^<]+)<', svg, re.IGNORECASE)

    if artist_match and song_match:
        artist = html.unescape(artist_match.group(1).strip())
        song = html.unescape(song_match.group(1).strip())
        is_playing = artist.lower() != "offline" and not re.search(
            r"not playing|nothing playing", song, re.IGNORECASE
        )
        return artist, song, is_playing

    if re.search(r"nothing playing on spotify", svg, re.IGNORECASE):
        return "Spotify", "Nothing playing right now", False

    return "Spotify", "Status unavailable", False


def truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def draw_spotify_icon(draw: ImageDraw.ImageDraw) -> None:
    cx, cy, r = 42, 56, 24
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill="#1db954")
    draw.arc((cx - 14, cy - 18, cx + 14, cy + 4), start=200, end=340, fill="#121212", width=3)
    draw.arc((cx - 10, cy - 10, cx + 10, cy + 10), start=200, end=340, fill="#121212", width=3)
    draw.arc((cx - 6, cy - 2, cx + 6, cy + 18), start=200, end=340, fill="#121212", width=3)


def draw_equalizer(draw: ImageDraw.ImageDraw, *, active: bool) -> None:
    left, right, bottom = 20, 320, 104
    bar_count = len(EQ_HEIGHTS)
    gap = 2
    bar_width = (right - left - gap * (bar_count - 1)) / bar_count

    for index, height in enumerate(EQ_HEIGHTS):
        x0 = left + index * (bar_width + gap)
        x1 = x0 + bar_width
        bar_height = height if active else 3
        y1 = bottom
        y0 = y1 - bar_height
        draw.rounded_rectangle((x0, y0, x1, y1), radius=1, fill="#1db954")


def build_png(artist: str, song: str, is_playing: bool, output: Path) -> None:
    width, height = 340, 112
    image = Image.new("RGB", (width, height), "#121212")
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=10, outline="#2a2a2a")
    draw_spotify_icon(draw)

    artist_font = load_font(18, bold=True)
    song_font = load_font(16)
    draw.text((84, 28), truncate(artist, 28), fill="#ffffff", font=artist_font)
    draw.text((84, 54), truncate(song, 32), fill="#b3b3b3", font=song_font)
    draw_equalizer(draw, active=is_playing)

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG")


def main() -> int:
    try:
        svg = fetch_svg()
    except urllib.error.URLError as exc:
        print(f"Failed to fetch Spotify status: {exc}", file=sys.stderr)
        return 1

    artist, song, is_playing = parse_track(svg)
    build_png(artist, song, is_playing, OUTPUT)
    print(f"Wrote {OUTPUT} ({artist}: {song}, playing={is_playing})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
