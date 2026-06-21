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

SPOTIFY_LOGO_PATH = (
    "M248 8C111.1 8 0 119.1 0 256s111.1 248 248 248 248-111.1 248-248S384.9 8 248 8zm100.7 364.9"
    "c-4.2 0-6.8-1.3-10.7-3.6-62.4-37.6-135-39.2-206.7-24.5-3.9 1-9 0.6-12.3-3.3-1.2-2.6-2.6-4.9-3.6-7.3-1.2-4.2-.4-9.8 4.5-12.8"
    " 3.1-1.9 6.6-2.9 10.1-3.7 78.5-20.3 155.7-14.6 219.3-8.5 19.8 2.2 39.9 6.2 56.7 12.7 3.1 1.2 5.5 3 7.5 6.1"
    " 2.7 4.8 2.4 9.8-1.1 13.8-2.5 2.9-6.1 4.6-10.3 5.1zm9.4-49.9c-4.2 0-6.8-1.3-10.7-3.6-62.4-37.6-135-39.2-206.7-24.5-3.9 1-9 0.6-12.3-3.3-1.2-2.6-2.6-4.9-3.6-7.3-2.7-4.8-2.4-9.8"
    " 1.1-13.8 2.5-2.9 6.1-4.6 10.3-5.1 72.2-14.8 147.9-6.2 212.3-8.5 20.8-2.2 41.7-1.3 62.9 5.4 3.1 1.2 5.5 3 7.5 6.1"
    " 2.7 4.8 2.4 9.8-1.1 13.8-2.5 2.9-6.1 4.6-10.3 5.1-62 12.8-127.7 14.6-195.7 5.4zm8.4-49.6c-4.2 0-6.8-1.3-10.7-3.6-62.4-37.6-135-39.2-206.7-24.5-3.9 1-9 0.6-12.3-3.3-1.2-2.6-2.6-4.9-3.6-7.3-2.7-4.8-2.4-9.8"
    " 1.1-13.8 2.5-2.9 6.1-4.6 10.3-5.1 72.2-14.8 147.9-6.2 212.3-8.5 20.8-2.2 41.7-1.3 62.9 5.4 3.1 1.2 5.5 3 7.5 6.1 2.7 4.8 2.4 9.8-1.1 13.8-2.5 2.9-6.1 4.6-10.3 5.1-62 12.8-127.7 14.6-195.7 5.4z"
)

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
  <g transform="translate(27, 41) scale(0.059)">
    <path fill="#1db954" d="{SPOTIFY_LOGO_PATH}"/>
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
