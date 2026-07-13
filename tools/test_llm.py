"""Vérifie la connexion à Hermes / LLM local (via LiteLLM proxy)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.brain import complete

print("=== Test LLM ===")
response = complete("Réponds juste 'OK' pour confirmer que tu fonctionnes.", max_tokens=200)
print(f"Réponse : {response!r}")
assert response.strip(), "Réponse vide — vérifier max_tokens et le modèle"
print("✓ LLM opérationnel")
