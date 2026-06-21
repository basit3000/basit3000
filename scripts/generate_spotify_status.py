#!/usr/bin/env python3
"""Generate a Spotify now-playing PNG for the GitHub profile README."""

from __future__ import annotations

import html
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

try:
    import cairosvg
except ImportError:  # pragma: no cover - local fallback without cairo
    cairosvg = None

SPOTIFY_UID = os.environ.get("SPOTIFY_UID", "ic9zxmbzknyeuiza6yh988k8n")
OUTPUT = Path(os.environ.get("OUTPUT_PATH", "assets/spotify-now-playing.png"))
EQ_BAR_COUNT = 70

SPOTIFY_VIEW_URL = (
    "https://spotify-github-profile.kittinanx.com/api/view"
    f"?uid={SPOTIFY_UID}&cover_image=false&theme=compact"
    "&show_offline=true&background_color=121212"
)

SPOTIFY_ICON_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 496 512">
  <path fill="#1db954" d="M248 8C111.1 8 0 119.1 0 256s111.1 248 248 248 248-111.1 248-248S384.9 8 248 8zm100.7 364.9c-4.2 0-6.8-1.3-10.7-3.6-62.4-37.6-135-39.2-206.7-24.5-3.9 1-9 0.6-12.3-3.3-1.2-2.6-2.6-4.9-3.6-7.3-1.2-4.2-.4-9.8 4.5-12.8 3.1-1.9 6.6-2.9 10.1-3.7 78.5-20.3 155.7-14.6 219.3-8.5 19.8 2.2 39.9 6.2 56.7 12.7 3.1 1.2 5.5 3 7.5 6.1 2.7 4.8 2.4 9.8-1.1 13.8-2.5 2.9-6.1 4.6-10.3 5.1zm9.4-49.9c-4.2 0-6.8-1.3-10.7-3.6-62.4-37.6-135-39.2-206.7-24.5-3.9 1-9 0.6-12.3-3.3-1.2-2.6-2.6-4.9-3.6-7.3-2.7-4.8-2.4-9.8 1.1-13.8 2.5-2.9 6.1-4.6 10.3-5.1 72.2-14.8 147.9-6.2 212.3-8.5 20.8-2.2 41.7-1.3 62.9 5.4 3.1 1.2 5.5 3 7.5 6.1 2.7 4.8 2.4 9.8-1.1 13.8-2.5 2.9-6.1 4.6-10.3 5.1-62 12.8-127.7 14.6-195.7 5.4zm8.4-49.6c-4.2 0-6.8-1.3-10.7-3.6-62.4-37.6-135-39.2-206.7-24.5-3.9 1-9 0.6-12.3-3.3-1.2-2.6-2.6-4.9-3.6-7.3-2.7-4.8-2.4-9.8 1.1-13.8 2.5-2.9 6.1-4.6 10.3-5.1 72.2-14.8 147.9-6.2 212.3-8.5 20.8-2.2 41.7-1.3 62.9 5.4 3.1 1.2 5.5 3 7.5 6.1 2.7 4.8 2.4 9.8-1.1 13.8-2.5 2.9-6.1 4.6-10.3 5.1-62 12.8-127.7 14.6-195.7 5.4z"/>
</svg>
"""

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


def spotify_green(alpha: float) -> tuple[int, int, int]:
    base = (29, 185, 84)
    background = (18, 18, 18)
    return tuple(
        int(background[index] + (base[index] - background[index]) * alpha)
        for index in range(3)
    )


def load_spotify_icon(size: int = 30) -> Image.Image:
    if cairosvg is None:
        raise RuntimeError("cairosvg is required to render the Spotify icon")

    png_bytes = cairosvg.svg2png(
        bytestring=SPOTIFY_ICON_SVG.encode("utf-8"),
        output_width=size,
        output_height=size,
    )
    return Image.open(BytesIO(png_bytes)).convert("RGBA")


def equalizer_bar_height(index: int, timestamp: float) -> tuple[float, float]:
    """Mirror the portfolio equalizer timing — returns height and opacity."""
    duration_ms = 350 + (index * 13) % 150
    delay_ms = (index * 41) % 280
    phase = ((timestamp * 1000 + delay_ms) % (duration_ms * 2)) / duration_ms
    wave = phase if phase <= 1 else 2 - phase
    height = 3 + wave * 11
    opacity = 0.35 + wave * 0.65
    return height, opacity


def draw_equalizer(draw: ImageDraw.ImageDraw, *, active: bool, timestamp: float | None = None) -> None:
    if not active:
        return

    left, right, bottom = 20, 320, 104
    gap = 2
    bar_width = (right - left - gap * (EQ_BAR_COUNT - 1)) / EQ_BAR_COUNT
    now = timestamp if timestamp is not None else time.time()

    for index in range(EQ_BAR_COUNT):
        height, opacity = equalizer_bar_height(index, now)
        x0 = left + index * (bar_width + gap)
        x1 = x0 + bar_width
        y1 = bottom
        y0 = y1 - height
        draw.rounded_rectangle(
            (x0, y0, x1, y1),
            radius=1,
            fill=spotify_green(opacity),
        )


def build_png(artist: str, song: str, is_playing: bool, output: Path) -> None:
    width, height = 340, 112
    image = Image.new("RGB", (width, height), "#121212")
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=10, outline="#2a2a2a")

    icon = load_spotify_icon(30)
    image.paste(icon, (27, 41), icon)

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
