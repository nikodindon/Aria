"""Tâche : poster un tweet quotidien autonome."""
from pathlib import Path
from core.brain import complete
from core.personality import format_mood_for_prompt
from bridge.twitter import post_tweet


def run():
    print("[task:daily_post] Composition du tweet du jour...")
    prompt_tpl = Path("prompts/tweet_compose.txt").read_text()
    mood = format_mood_for_prompt()
    prompt = prompt_tpl.format(mood=mood, news_summary="(pas de news chargées)")
    tweet = complete(prompt, max_tokens=300)
    print(f"[task:daily_post] Tweet : {tweet}")
    # post_tweet(tweet)  # décommenter quand l'API X est configurée
