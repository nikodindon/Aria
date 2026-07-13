"""
plugins/agent_delegate.py — Delegation de taches a un agent externe.

Quand ARIA n'a pas la connaissance necessaire (question sur
l'actualite, fait recent, recherche), elle peut deleguer a un
autre agent (ici : Hermes) qui a acces au web.

L'agent retourne une reponse textuelle courte qu'ARIA peut
integrer dans sa conversation WhatsApp.

Configuration :
  DELEGATE_CMD = ["hermes", "chat", "-q"]  # commande a invoquer
  DELEGATE_TIMEOUT = 30  # secondes max

Usage typique (depuis aria_loop) :
  from plugins.agent_delegate import ask_helper_agent
  answer = ask_helper_agent("C'est quoi la meteo a Paris demain ?")

KISS : subprocess simple, pas de streaming, pas de retry.
"""
import subprocess
import time
import re
import shutil
from pathlib import Path

# Commande a invoquer. On teste d'abord si hermes est dispo, sinon
# fallback sur d'autres agents. Le -q est pour "single query".
DELEGATE_CMD = ["hermes", "chat", "-q"]
DELEGATE_TIMEOUT = 30  # secondes


def is_available() -> bool:
    """Retourne True si l'agent helper est disponible (binaire trouve)."""
    # shutil.which cherche dans le PATH
    return shutil.which(DELEGATE_CMD[0]) is not None


def ask_helper_agent(query: str, timeout: int = DELEGATE_TIMEOUT) -> str | None:
    """Pose une question a l'agent helper. Retourne sa reponse ou None.

    L'agent va :
    1. Analyser la question
    2. Faire des recherches web si besoin
    3. Synthetiser une reponse concise

    Renvoie None si l'agent n'est pas dispo, timeout, ou si
    quelque chose a foire. Le caller doit gerer le None.
    """
    if not is_available():
        return None

    # On ajoute une instruction systeme pour forcer une reponse
    # COURTE (limite WhatsApp < 280 chars idealement, et l'agent
    # n'a pas besoin de blabla).
    full_prompt = (
        f"{query}\n\n"
        "IMPORTANT : Reponds en francais, en 1-3 phrases MAXIMUM, "
        "sans markdown, sans emojis, sans preface ni politesse. "
        "Juste la reponse directe et concise."
    )

    try:
        proc = subprocess.run(
            DELEGATE_CMD + [full_prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"[timeout apres {timeout}s]"
    except Exception as e:
        return f"[erreur: {e}]"

    if proc.returncode != 0:
        return f"[agent a plante, code {proc.returncode}]"

    # La sortie de hermes chat contient du bruit (les borders ╭─ ╰,
    # les logs de tools, etc). On extrait juste le contenu entre les
    # borders. Format typique :
    #   ╭─ ⚕ Hermes ─...
    #       Ma reponse...
    #   ╰─...─╯
    output = proc.stdout
    return _extract_answer(output)


def _extract_answer(output: str) -> str:
    """Extrait la reponse utile de la sortie de hermes chat.

    Le format de hermes chat est :
      [bruit] (preparation, search logs)
      ╭─ ⚕ Hermes ─...
          Ma reponse
      ╰─...─╯
      [bruit] (session ID, etc)

    On cherche le contenu entre le premier ╭ et le ╰ correspondant.
    """
    lines = output.splitlines()
    in_block = False
    answer_lines = []
    for line in lines:
        if line.startswith("╭─"):
            in_block = True
            continue
        if line.startswith("╰─"):
            in_block = False
            continue
        if in_block:
            # Enleve les indentations (4 espaces typiques)
            stripped = line.lstrip()
            if stripped:
                answer_lines.append(stripped)
    if not answer_lines:
        # Pas de bloc trouve : on retourne tout sauf le bruit evident
        # (les ┊ qui sont des logs de tools)
        clean = "\n".join(
            l for l in lines
            if not l.strip().startswith("┊")
            and "Resume this session" not in l
            and "Session:" not in l
            and "Duration:" not in l
            and "Messages:" not in l
        )
        return clean.strip() or output.strip()
    return " ".join(answer_lines).strip()


# === Detection des besoins de delegation ===

# Mots-cles qui suggerent qu'ARIA devrait deleguer a l'agent web.
# On reste conservateur : on prefere un faux negatif (ARIA repond
# sans chercher) qu'un faux positif (ARIA delegue pour rien).
DELEGATION_KEYWORDS = [
    # Recherches d'info
    r"\bcherche\b", r"\btrouve\b", r"\bsearch\b", r"\bfind\b",
    r"\bc'est quoi\b", r"\bwhat is\b", r"\bqui est\b", r"\bwho is\b",
    r"\bdéfinition\b", r"\bdefinition\b",
    # Actualite
    r"\bactu\b", r"\bactu(?:alité)?s?\b", r"\bnews\b",
    r"\bdernières?\s+nouvelles?\b", r"\blast\b",
    r"\bmaintenant\b", r"\bnow\b", r"\b2026\b", r"\b2027\b",
    r"\baujourd'hui\b", r"\btoday\b", r"\bcette semaine\b", r"\bthis week\b",
    # Meteo / lieu specifique
    r"\bmétéo\b", r"\bweather\b", r"\btempérature\b", r"\btemperature\b",
    # Prix / finance
    r"\bprix\b", r"\bprice\b", r"\bcours\b", r"\bstock\b",
    r"\bbourse\b", r"\bbitcoin\b", r"\bbtc\b", r"\beth\b",
    # Evenement
    r"\bquand\b", r"\bwhen\b", r"\bdate\b", r"\bévénement\b",
    r"\bmatch\b", r"\bélection\b", r"\belection\b",
]

# Compile une fois pour perf
_DELEGATION_RE = re.compile(
    "|".join(DELEGATION_KEYWORDS),
    re.IGNORECASE,
)


def needs_delegation(message: str) -> bool:
    """Retourne True si le message suggere qu'ARIA devrait deleguer.

    Heuristique KISS : on cherche des mots-cles. Si oui, on delegue.
    Le helper agent est rapide (10-15s) et a toujours raison de
    chercher plutot que d'inventer, donc on est bias vers le oui.
    """
    if not message or len(message) < 5:
        return False
    return bool(_DELEGATION_RE.search(message))


def delegate_for_message(message: str) -> str | None:
    """Si le message necessite une recherche, delegue et renvoie la reponse.

    Sinon, renvoie None (le caller continue avec le LLM normal).
    """
    if not needs_delegation(message):
        return None
    # Reformule en query concise pour l'agent
    query = message.strip()
    # Limite la longueur de la query pour eviter les timeout
    if len(query) > 200:
        query = query[:200] + "..."
    return ask_helper_agent(query)


if __name__ == "__main__":
    # Test en CLI
    import sys
    if len(sys.argv) < 2:
        print("Usage: python plugins/agent_delegate.py '<question>'")
        sys.exit(1)
    q = " ".join(sys.argv[1:])
    print(f"is_available: {is_available()}")
    print(f"needs_delegation: {needs_delegation(q)}")
    print(f"---")
    answer = ask_helper_agent(q)
    print(f"answer: {answer}")
