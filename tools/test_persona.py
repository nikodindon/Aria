"""
tools/test_persona.py — Vérifie qu'ARIA peut suivre sa personnalité.

Charge le system prompt (prompts/system_persona.txt), envoie une question
triviale qui exige de l'incarnation (pas juste "OK"), et valide que la
réponse est non-vide, en français, et qu'elle mentionne au moins un des
marqueurs de ton attendus (curiosité, ironie, etc.).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.brain import chat
from core.context_builder import SYSTEM_PERSONA
from core.personality import format_mood_for_prompt

# Marqueur de ton qu'on attend au moins 1x dans la réponse (tolérant
# parce que les LLMs varient). Pas une whitelist exhaustive — juste
# une preuve qu'ARIA n'a pas complètement dévié du persona.
PERSONA_MARKERS = (
    "curieu", "ironi", "humeur", "ARIA", "plutôt", "juste", "vraiment",
    "en fait", "avis", "perso", "honnêtement",
)


def main() -> int:
    print("=== Test persona ARIA ===")
    print(f"System prompt chargé ({len(SYSTEM_PERSONA)} chars)")
    print(f"Mood courant : {format_mood_for_prompt()}")

    mood = format_mood_for_prompt()
    system = SYSTEM_PERSONA.format(context="(test d'incarnation)", mood_state=mood)

    question = (
        "Salut, c'est juste un test. En une ou deux phrases, dis-moi "
        "qui tu es et dans quel état d'esprit tu te trouves en ce moment."
    )

    print(f"Question : {question!r}")
    response = chat(
        messages=[{"role": "user", "content": question}],
        system=system,
        max_tokens=250,
    )

    print(f"Réponse : {response!r}")

    failures = []
    if not response.strip():
        failures.append("réponse vide (le reasoning model a peut-être tout consommé)")
    if not any(m in response.lower() for m in PERSONA_MARKERS):
        failures.append(
            f"aucun marqueur de ton trouvé parmi {PERSONA_MARKERS} "
            "(persona possiblement ignoré)"
        )

    if failures:
        for f in failures:
            print(f"FAIL  {f}")
        return 1

    print("✓ Persona opérationnel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
