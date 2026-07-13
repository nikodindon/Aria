"""
plugins/app_actions.py — Catalogue d'actions physiques pilotables par ARIA.

Quand Hermes (LLM) decide qu'il faut agir physiquement sur le
telephone (ouvrir une app, chercher du contenu, etc.), il peut
emettre une reponse contenant un tag [ACTION] que ce module parse
et execute via ADB.

Format du tag (en francais KISS) :
  [ACTION] open_app|youtube
  [ACTION] open_app|com.google.android.youtube
  [ACTION] open_url|https://www.youtube.com/watch?v=XXXX
  [ACTION] open_youtube_search|funny cats compilation
  [ACTION] shell_echo|hello world         (debug, juste pour tester)

Pour ajouter une nouvelle action :
1. Ecrire une fonction `action_<name>(args) -> str` qui fait
   l'action et retourne un message de confirmation/resultat.
2. L'enregistrer dans ACTIONS.

Le LLM decide QUAND utiliser [ACTION] en fonction du system
prompt qui lui est envoye (voir prompts/whatsapp_reply.txt).
"""
import shlex
import subprocess
import time
from pathlib import Path

# === Mapping nom lisible -> package name ===
# Hermes dit "youtube" et on traduit en "com.google.android.youtube".
APP_PACKAGES = {
    "youtube": "com.google.android.youtube",
    "yt": "com.google.android.youtube",
    "whatsapp": "com.whatsapp",
    "wa": "com.whatsapp",
    "chrome": "com.android.chrome",
    "browser": "com.android.chrome",
    "spotify": "com.spotify.music",
    "maps": "com.google.android.apps.maps",
    "google maps": "com.google.android.apps.maps",
    "gmail": "com.google.android.gm",
    "mail": "com.google.android.gm",
    "telegram": "org.telegram.messenger",
    "tg": "org.telegram.messenger",
    "settings": "com.android.settings",
    "parametres": "com.android.settings",
    "camera": "com.android.camera",
    "appareil photo": "com.android.camera",
    "calculatrice": "com.android.calculator2",
    "calculator": "com.android.calculator2",
}


# === Actions ===

def action_open_app(args: str) -> str:
    """Ouvre une app par son nom lisible (youtube, whatsapp, etc.).

    Accepte aussi un package name direct (commence par 'com.').
    Hermes dit 'youtube' et on traduit en com.google.android.youtube.
    """
    from bridge.adb import open_app as adb_open_app

    name = args.strip().strip("'\"")
    # Si c'est deja un package name (commence par com.)
    if name.startswith("com.") or "." in name:
        package = name
        display = name
    else:
        key = name.lower()
        package = APP_PACKAGES.get(key)
        if not package:
            # Liste les apps connues pour aider Hermes
            known = ", ".join(sorted(set(APP_PACKAGES.keys())))
            return f"Je connais pas l'app '{name}'. Apps connues : {known}"
        display = name

    adb_open_app(package)
    time.sleep(1.5)  # laisse l'app s'ouvrir
    return f"J'ai ouvert {display} ({package}) sur le telephone."


def action_open_url(args: str) -> str:
    """Ouvre une URL dans le navigateur par defaut.

    Utile pour ouvrir une page web, une video YouTube directe, etc.
    """
    import shlex
    from bridge.adb import _adb

    url = args.strip().strip("'\"")
    if not url.startswith("http"):
        return f"URL invalide (doit commencer par http): {url}"
    # am start -a android.intent.action.VIEW -d <url>
    _adb("shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url)
    time.sleep(1.5)
    return f"J'ai ouvert l'URL {url} dans le navigateur."


def action_open_youtube_search(args: str) -> str:
    """Ouvre YouTube avec une recherche.

    Equivalent a : youtube.com/results?search_query=<query>
    """
    from bridge.adb import _adb

    query = args.strip().strip("'\"")
    if not query:
        return "Recherche vide, dis-moi ce que tu veux chercher."
    # Utilise l'URL de recherche YouTube
    from urllib.parse import quote
    url = f"https://www.youtube.com/results?search_query={quote(query)}"
    _adb("shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url)
    time.sleep(1.5)
    return f"J'ai ouvert YouTube avec la recherche '{query}'."


def action_shell_echo(args: str) -> str:
    """Action debug : juste echo. Sert a tester le pipeline."""
    return f"shell_echo: {args}"


# === Catalogue ===

ACTIONS = {
    "open_app": action_open_app,
    "open_url": action_open_url,
    "open_youtube_search": action_open_youtube_search,
    "shell_echo": action_shell_echo,  # debug
}


# === Parsing du tag [ACTION] ===

import re as _re

# Format : [ACTION] name|arg1|arg2|...
# On accepte espaces autour du |, et les guillemets pour les args composes.
_ACTION_RE = _re.compile(r"\[ACTION\]\s*([a-z_]+)(?:\s*(?:\|(.+)))?", _re.IGNORECASE)


def parse_action(response: str) -> tuple[str, str] | None:
    """Parse un tag [ACTION] dans la reponse du LLM.

    Retourne (action_name, args_str) ou None si pas de tag.
    Args_str peut etre vide.
    """
    m = _ACTION_RE.search(response)
    if not m:
        return None
    name = m.group(1).lower()
    args = (m.group(2) or "").strip()
    return (name, args)


def execute_action(name: str, args: str) -> str:
    """Execute une action et retourne le message de resultat.

    Si l'action est inconnue, retourne un message d'erreur.
    """
    action_fn = ACTIONS.get(name)
    if not action_fn:
        known = ", ".join(sorted(ACTIONS.keys()))
        return f"Action inconnue '{name}'. Actions connues : {known}"
    try:
        return action_fn(args)
    except Exception as e:
        return f"Action '{name}' a plante: {e}"


# === CLI de test ===

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python plugins/app_actions.py '<message avec [ACTION]>'")
        print("Ex:   python plugins/app_actions.py 'ouvre [ACTION] open_app|youtube stp'")
        sys.exit(1)
    msg = sys.argv[1]
    parsed = parse_action(msg)
    if not parsed:
        print("Aucun tag [ACTION] trouve dans le message.")
        sys.exit(1)
    name, args = parsed
    print(f"Action: {name}({args!r})")
    result = execute_action(name, args)
    print(f"Resultat: {result}")
