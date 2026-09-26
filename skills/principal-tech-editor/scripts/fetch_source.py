#!/usr/bin/env python3
"""
Source fetcher for Principal Tech Editor.
Extracts YouTube transcripts or web article text and metadata.
"""

import sys
import os
import re
import json
import argparse
import ssl
import urllib.request
import urllib.parse
from pathlib import Path

# Setup SSL context that works cleanly on macOS
try:
    ssl_context = ssl.create_default_context()
except Exception:
    ssl_context = ssl._create_unverified_context()

unverified_context = ssl._create_unverified_context()

def make_request(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        with urllib.request.urlopen(req, timeout=timeout, context=unverified_context) as resp:
            return resp.read().decode("utf-8", errors="ignore")

def extract_youtube_id(url: str) -> str | None:
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
        r"youtube\.com\/live\/([0-9A-Za-z_-]{11})"
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None

def fetch_youtube_metadata(video_id: str) -> dict:
    url = f"https://www.youtube.com/watch?v={video_id}"
    meta = {"title": "", "date": "", "channel": "", "url": url, "type": "youtube"}
    try:
        html = make_request(url, timeout=10)
        title_m = re.search(r"<title>(.*?)</title>", html)
        if title_m:
            meta["title"] = title_m.group(1).replace(" - YouTube", "").strip()
        date_m = re.search(r'"publishDate":"(.*?)"', html)
        if date_m:
            meta["date"] = date_m.group(1)
        author_m = re.search(r'"author":"(.*?)"', html)
        if author_m:
            meta["channel"] = author_m.group(1)
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to fetch YouTube metadata: {e}\n")
    return meta

def fetch_youtube_transcript(video_id: str, with_timestamps: bool = True) -> str:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id)
    except Exception:
        import subprocess
        cmd = [
            "uv", "run", "--with", "youtube-transcript-api", "python3", "-c",
            f"""
import json
from youtube_transcript_api import YouTubeTranscriptApi
api = YouTubeTranscriptApi()
t = api.fetch('{video_id}')
print(json.dumps([{{'start': item.start, 'duration': item.duration, 'text': item.text}} for item in t]))
"""
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        raw_json = res.stdout.strip().splitlines()[-1]
        data = json.loads(raw_json)
        class Snippet:
            def __init__(self, d):
                self.start = d['start']
                self.duration = d['duration']
                self.text = d['text']
        transcript = [Snippet(x) for x in data]

    def fmt_time(seconds):
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

    blocks = []
    cur_text = []
    cur_start = 0.0

    for item in transcript:
        clean_text = item.text.replace("\n", " ").strip()
        if not clean_text:
            continue
        if not cur_text:
            cur_start = item.start
        
        if ">>" in clean_text and len(cur_text) > 0:
            blocks.append((cur_start, " ".join(cur_text)))
            cur_text = [clean_text.replace(">>", "").strip()]
            cur_start = item.start
            continue

        clean_text = clean_text.replace(">>", "").strip()
        cur_text.append(clean_text)

        dur = (item.start + item.duration) - cur_start
        if dur >= 35 and (clean_text.endswith(".") or clean_text.endswith("?") or clean_text.endswith("!")):
            blocks.append((cur_start, " ".join(cur_text)))
            cur_text = []

    if cur_text:
        blocks.append((cur_start, " ".join(cur_text)))

    lines = []
    for start, text in blocks:
        if with_timestamps:
            lines.append(f"[{fmt_time(start)}] {text}")
        else:
            lines.append(text)

    return "\n\n".join(lines)

def fetch_web_article(url: str) -> dict:
    html = make_request(url, timeout=15)

    title_m = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    title = title_m.group(1).strip() if title_m else ""

    body = re.sub(r"<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r"<[^>]+>", " ", body)
    body = re.sub(r"&[a-z]+;", " ", body)
    body = re.sub(r"\s+", " ", body).strip()

    return {
        "title": title,
        "date": "",
        "channel": "",
        "url": url,
        "type": "article",
        "content": body[:35000]
    }

def main():
    parser = argparse.ArgumentParser(description="Fetch YouTube transcripts or web article text.")
    parser.add_argument("url", help="URL to process")
    parser.add_argument("--no-timestamps", action="store_true", help="Omit timestamps from transcript")
    parser.add_argument("--json", action="store_true", help="Output full JSON envelope with metadata")

    args = parser.parse_args()

    yt_id = extract_youtube_id(args.url)
    if yt_id:
        meta = fetch_youtube_metadata(yt_id)
        transcript = fetch_youtube_transcript(yt_id, with_timestamps=not args.no_timestamps)
        meta["content"] = transcript
        if args.json:
            print(json.dumps(meta, indent=2))
        else:
            print(f"Title: {meta.get('title')}")
            print(f"Channel: {meta.get('channel')}")
            print(f"Date: {meta.get('date')}")
            print(f"URL: {meta.get('url')}\n")
            print(transcript)
    else:
        article = fetch_web_article(args.url)
        if args.json:
            print(json.dumps(article, indent=2))
        else:
            print(f"Title: {article.get('title')}")
            print(f"URL: {article.get('url')}\n")
            print(article.get("content", ""))

if __name__ == "__main__":
    main()
