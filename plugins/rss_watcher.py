"""
plugins/rss_watcher.py — Lecteur de flux RSS pour ARIA.

Permet a ARIA de suivre des sources d'actu et de forger des
opinions. Stocke les titres dans la table `knowledge` de la DB
ARIA pour reutilisation ulterieure (par le LLM, par le journal,
par les posts X, etc.).

API :
  fetch_feed(url) -> list[dict]   : fetch un flux RSS, retourne
                                    les items (title, link, pubDate)
  fetch_all() -> int              : fetch tous les flux configures,
                                    retourne le nombre d'items
                                    inseres en DB
  get_recent_news(limit, topic)   : recupere les news stockees,
                                    filtre par topic si specifie

Par defaut, on suit Hacker News (tech, anglais). Ajouter Le Monde,
NYT, etc. dans DEFAULT_FEEDS pour etendre.
"""
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.memory import get_conn


DEFAULT_FEEDS = {
    "hackernews": "https://news.ycombinator.com/rss",
    # "lemonde_tech": "https://www.lemonde.fr/pixels/rss_full.xml",
    # On peut en ajouter d'autres. Desactives par defaut pour
    # eviter le bruit.
}


def _http_get(url: str, timeout: int = 15) -> str:
    """GET HTTP avec un user-agent standard (certains flux RSS
    refusent les requetes sans UA)."""
    req = Request(url, headers={"User-Agent": "ARIA/0.1 (+local RSS reader)"})
    with urlopen(req, timeout=timeout) as resp:
        # RSS est en XML, on retourne en bytes puis on decode
        return resp.read().decode("utf-8", errors="replace")


def _parse_rss(xml_text: str) -> list[dict]:
    """Parse un flux RSS 2.0, retourne les items.

    Limitation KISS : on ne gere que RSS 2.0 (pas Atom).
    Pour un parseur plus robuste, utiliser feedparser.
    """
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    channel = root.find("channel")
    if channel is None:
        return items
    for item in channel.findall("item"):
        title_el = item.find("title")
        link_el = item.find("link")
        pub_el = item.find("pubDate")
        desc_el = item.find("description")
        items.append({
            "title": title_el.text if title_el is not None else "",
            "link": link_el.text if link_el is not None else "",
            "pubDate": pub_el.text if pub_el is not None else "",
            "description": desc_el.text if desc_el is not None else "",
        })
    return items


def fetch_feed(url: str) -> list[dict]:
    """Fetch un flux RSS et retourne la liste d'items (sans toucher la DB)."""
    try:
        xml = _http_get(url)
    except (URLError, TimeoutError, OSError) as e:
        print(f"[rss] fetch failed for {url}: {e}")
        return []
    return _parse_rss(xml)


def save_to_knowledge(items: list[dict], topic: str) -> int:
    """Insere les items dans la table `knowledge`.

    On dedup par titre : si un titre existe deja, on l'ignore.
    C'est grossier (le meme article peut apparaitre avec un titre
    legerement different entre 2 runs) mais ca suffit pour eviter
    de remplir la DB avec 1000x le meme truc.

    Retourne le nombre d'items inseres.
    """
    if not items:
        return 0
    conn = get_conn()
    now = datetime.now().isoformat()
    inserted = 0
    for item in items:
        title = (item.get("title") or "").strip()
        if not title:
            continue
        # Dedup : SELECT existant
        existing = conn.execute(
            "SELECT 1 FROM knowledge WHERE topic=? AND content=? LIMIT 1",
            (topic, title)
        ).fetchone()
        if existing:
            continue
        conn.execute(
            "INSERT INTO knowledge (ts, topic, content, source) VALUES (?,?,?,?)",
            (now, topic, title, item.get("link", ""))
        )
        inserted += 1
    conn.commit()
    conn.close()
    return inserted


def fetch_all(feeds: Optional[dict] = None) -> int:
    """Fetch tous les flux configures et insere en DB.

    Retourne le nombre total d'items inseres.
    """
    feeds = feeds or DEFAULT_FEEDS
    total = 0
    for topic, url in feeds.items():
        items = fetch_feed(url)
        n = save_to_knowledge(items, topic=topic)
        print(f"[rss] {topic}: {n} nouveaux items (sur {len(items)} fetched)")
        total += n
    return total


def get_recent_news(limit: int = 10, topic: Optional[str] = None) -> list[dict]:
    """Recupere les news stockees en DB, triees par date DESC.

    Si topic est specifie, filtre par topic (ex: 'hackernews').
    """
    conn = get_conn()
    if topic:
        rows = conn.execute(
            "SELECT * FROM knowledge WHERE topic=? ORDER BY ts DESC LIMIT ?",
            (topic, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM knowledge ORDER BY ts DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def news_summary_for_prompt(limit: int = 5) -> str:
    """Retourne un resume des news recentes formate pour inclusion
    dans un prompt LLM."""
    news = get_recent_news(limit=limit)
    if not news:
        return "(aucune news recente)"
    lines = [f"- [{n['topic']}] {n['content']}" for n in news]
    return "\n".join(lines)


if __name__ == "__main__":
    # Test : fetch les flux et affiche les 5 derniers
    print("=== Fetch RSS feeds ===")
    n = fetch_all()
    print(f"Total insere: {n}")
    print()
    print("=== 5 dernieres news ===")
    for item in get_recent_news(limit=5):
        print(f"  [{item['topic']}] {item['content'][:80]}")
