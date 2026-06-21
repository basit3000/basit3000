#!/usr/bin/env python3
"""Generate a Spotify now-playing SVG for the GitHub profile README."""

from __future__ import annotations

import html
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

SPOTIFY_UID = os.environ.get("SPOTIFY_UID", "ic9zxmbzknyeuiza6yh988k8n")
OUTPUT = Path(os.environ.get("OUTPUT_PATH", "assets/spotify-now-playing.svg"))

SPOTIFY_VIEW_URL = (
    "https://spotify-github-profile.kittinanx.com/api/view"
    f"?uid={SPOTIFY_UID}&cover_image=false&theme=compact"
    "&show_offline=true&background_color=121212"
)

SPOTIFY_ICON_PATH = (
    "M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"
)

SPOTIFY_ICON_SCALE = 28 / 24

EQ_BAR_COUNT = 70


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


def build_equalizer_svg(active: bool) -> str:
    if not active:
        return ""

    left, width, gap, bottom = 20, 300, 2, 104
    bar_width = (width - gap * (EQ_BAR_COUNT - 1)) / EQ_BAR_COUNT
    bars = []

    for index in range(EQ_BAR_COUNT):
        duration = 350 + (index * 13) % 150
        delay = (index * 41) % 280
        x = left + index * (bar_width + gap)
        bars.append(
            f'<rect class="eq-bar" x="{x:.2f}" y="{bottom - 3:.2f}" '
            f'width="{bar_width:.2f}" height="3" rx="1" fill="#1db954">'
            f'<animate attributeName="height" values="3;14;3" dur="{duration}ms" '
            f'begin="{delay}ms" repeatCount="indefinite"/>'
            f'<animate attributeName="y" values="{bottom - 3:.2f};{bottom - 14:.2f};{bottom - 3:.2f}" '
            f'dur="{duration}ms" begin="{delay}ms" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0.35;1;0.35" dur="{duration}ms" '
            f'begin="{delay}ms" repeatCount="indefinite"/>'
            f"</rect>"
        )

    return "\n    ".join(bars)


def build_svg(artist: str, song: str, is_playing: bool) -> str:
    artist_text = html.escape(truncate(artist, 28))
    song_text = html.escape(truncate(song, 32))
    equalizer = build_equalizer_svg(is_playing)

    return f"""<svg width="340" height="112" viewBox="0 0 340 112" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Spotify Now Playing">
  <title>Spotify Now Playing</title>
  <rect x="0.5" y="0.5" width="339" height="111" rx="10" fill="#121212" stroke="#2a2a2a"/>
  <g transform="translate(28, 42) scale({SPOTIFY_ICON_SCALE})">
    <path fill="#1db954" d="{SPOTIFY_ICON_PATH}"/>
  </g>
  <text x="84" y="44" fill="#ffffff" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="18" font-weight="700">{artist_text}</text>
  <text x="84" y="68" fill="#b3b3b3" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="16">{song_text}</text>
  {equalizer}
</svg>
"""


def main() -> int:
    try:
        source = fetch_svg()
    except urllib.error.URLError as exc:
        print(f"Failed to fetch Spotify status: {exc}", file=sys.stderr)
        return 1

    artist, song, is_playing = parse_track(source)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(build_svg(artist, song, is_playing), encoding="utf-8")
    print(f"Wrote {OUTPUT} ({artist}: {song}, playing={is_playing})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
