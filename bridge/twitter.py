"""
bridge/twitter.py — Interaction X/Twitter via API Tweepy
"""
import os
from dotenv import load_dotenv

load_dotenv()

try:
    import tweepy
    _HAS_TWEEPY = True
except ImportError:
    _HAS_TWEEPY = False


def get_client():
    if not _HAS_TWEEPY:
        raise ImportError("tweepy non installé — pip install tweepy")
    return tweepy.Client(
        bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
        consumer_key=os.getenv("TWITTER_API_KEY"),
        consumer_secret=os.getenv("TWITTER_API_SECRET"),
        access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.getenv("TWITTER_ACCESS_SECRET"),
    )


def post_tweet(text: str) -> str | None:
    client = get_client()
    resp = client.create_tweet(text=text)
    return resp.data["id"] if resp.data else None


def get_home_timeline(max_results: int = 10) -> list[dict]:
    client = get_client()
    resp = client.get_home_timeline(max_results=max_results)
    if not resp.data:
        return []
    return [{"id": t.id, "text": t.text} for t in resp.data]
