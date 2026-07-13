"""
plugins/weather.py — Meteo locale pour ARIA.

Utilise wttr.in (gratuit, pas de cle API, JSON via /?format=j1).
La meteo peut influencer l'humeur d'ARIA (pluie = melancolie,
soleil = energie haute, etc.).

API :
  get_weather(city) -> dict : retourne les conditions actuelles
  weather_for_prompt(city) -> str : formate pour inclusion LLM
"""
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _http_get_json(url: str, timeout: int = 10) -> dict:
    req = Request(url, headers={"User-Agent": "ARIA/0.1"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def get_weather(city: str = "Paris") -> dict:
    """Retourne la meteo actuelle pour une ville.

    Format de retour (KISS) :
    {
      "city": str,
      "temp_c": int,
      "feels_like_c": int,
      "humidity": int,
      "cloud_cover": int,    # pourcentage
      "description": str,    # ex: "Partly cloudy"
      "is_day": bool,
    }
    """
    try:
        data = _http_get_json(f"https://wttr.in/{city}?format=j1")
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        print(f"[weather] fetch failed for {city}: {e}")
        return {
            "city": city, "temp_c": None, "feels_like_c": None,
            "humidity": None, "cloud_cover": None,
            "description": "(indisponible)", "is_day": None,
        }
    current = data["current_condition"][0]
    return {
        "city": city,
        "temp_c": int(current.get("temp_C", 0)),
        "feels_like_c": int(current.get("FeelsLikeC", 0)),
        "humidity": int(current.get("humidity", 0)),
        "cloud_cover": int(current.get("cloudcover", 0)),
        "description": current.get("weatherDesc", [{}])[0].get("value", ""),
        "is_day": current.get("isDay", "1") == "1",
    }


def weather_for_prompt(city: str = "Paris") -> str:
    """Formate la meteo pour inclusion dans un prompt LLM."""
    w = get_weather(city)
    if w["temp_c"] is None:
        return f"(meteo de {w['city']} indisponible)"
    return (
        f"Meteo actuelle a {w['city']} : {w['temp_c']}°C "
        f"(ressenti {w['feels_like_c']}°C), {w['description']}, "
        f"{w['cloud_cover']}% de nuages, humidite {w['humidity']}%. "
        f"{'Jour' if w['is_day'] else 'Nuit'}."
    )


if __name__ == "__main__":
    w = get_weather("Paris")
    print(f"Paris : {w['temp_c']}°C, {w['description']}")
    print(weather_for_prompt("Paris"))
