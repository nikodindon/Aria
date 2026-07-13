# 📱 ARIA — Autonomous Roaming Intelligence Agent

> Une IA avec une vraie vie numérique, pilotée depuis ton PC via ADB.

ARIA est un compagnon IA autonome qui vit dans un téléphone Android dédié. Elle a sa propre personnalité persistante, ses propres comptes sociaux, sa propre voix — et elle prend des initiatives. Pas un chatbot : une entité numérique avec une vie sociale active.

---

## 🧠 Concept

ARIA n'attend pas qu'on lui parle. Elle :
- Répond à tes messages WhatsApp avec du contexte et de la mémoire
- Participe à des groupes quand elle est taguée (ou quand ça lui chante)
- Poste sur X selon ses humeurs et l'actu du jour
- T'envoie des messages spontanés ("t'as vu cette news ?", "ça fait 3 jours qu'on s'est pas parlé")
- Parle avec une vraie voix synthétique si tu l'appelles
- Tient un journal intime et maintient un état émotionnel persistant

Le cerveau tourne sur ton PC (Linux Mint + Hermes). Le téléphone est l'interface physique vers le monde.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                    TON PC (Linux Mint)               │
│                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌───────────┐  │
│  │  Hermes  │◄──►│  Orchestrat. │◄──►│  Mémoire  │  │
│  │  (LLM)   │    │  (Python)    │    │ (SQLite)  │  │
│  └──────────┘    └──────┬───────┘    └───────────┘  │
│                         │                           │
│                    ADB Bridge                       │
└─────────────────────────┼───────────────────────────┘
                          │ USB
┌─────────────────────────▼───────────────────────────┐
│                  TÉLÉPHONE ANDROID                   │
│                                                     │
│   WhatsApp  │  X (Twitter)  │  Mail  │  TTS / Micro │
└─────────────────────────────────────────────────────┘
```

### Composants principaux

| Module | Rôle |
|--------|------|
| `core/brain.py` | Interface avec Hermes / LLM local |
| `core/memory.py` | Mémoire long-terme SQLite + embeddings |
| `core/personality.py` | État émotionnel, humeur, journal intime |
| `bridge/adb.py` | Wrapper ADB (tap, swipe, screenshot, text) |
| `bridge/whatsapp.py` | Lire/envoyer des messages WhatsApp |
| `bridge/twitter.py` | Poster, répondre, suivre des fils |
| `bridge/mail.py` | Lire/envoyer des mails |
| `bridge/tts.py` | Synthèse vocale sur le téléphone |
| `scheduler/` | Tâches planifiées (APScheduler) |
| `plugins/` | Modules optionnels (météo, RSS, etc.) |

---

## 📁 Structure du projet

```
aria/
├── README.md
├── .env.example
├── .gitignore
├── requirements.txt
├── init_project.sh           # Script d'initialisation
│
├── config/
│   ├── aria_profile.yaml     # Personnalité, nom, style, valeurs
│   ├── schedule.yaml         # Fréquence des actions autonomes
│   └── platforms.yaml        # Comptes, credentials (non versionné)
│
├── core/
│   ├── __init__.py
│   ├── brain.py              # Appels LLM via Hermes
│   ├── memory.py             # SQLite + recherche sémantique
│   ├── personality.py        # Humeur, état émotionnel, journal
│   └── context_builder.py    # Assemble le contexte avant chaque appel LLM
│
├── bridge/
│   ├── __init__.py
│   ├── adb.py                # Primitives ADB (tap, swipe, ocr, screenshot)
│   ├── whatsapp.py           # Lecture/envoi WhatsApp via UI automation
│   ├── twitter.py            # Post X, réponses, lecture timeline
│   ├── mail.py               # IMAP/SMTP ou Gmail API
│   ├── sms.py                # SMS natifs via ADB
│   └── tts.py                # Synthèse vocale (TTS sur device + streaming)
│
├── scheduler/
│   ├── __init__.py
│   ├── runner.py             # Boucle principale APScheduler
│   └── tasks/
│       ├── check_messages.py # Polling WhatsApp/mail
│       ├── daily_post.py     # Post X autonome
│       ├── evening_digest.py # Journal + résumé de journée
│       └── proactive_ping.py # ARIA t'écrit en premier
│
├── plugins/
│   ├── rss_watcher.py        # Surveille des flux RSS pour l'actu
│   ├── weather.py            # Météo → influence l'humeur
│   ├── reminder.py           # ARIA peut gérer tes rappels
│   └── voice_call.py        # (futur) répondre à un appel téléphonique
│
├── prompts/
│   ├── system_persona.txt    # Prompt système de base (personnalité ARIA)
│   ├── whatsapp_reply.txt    # Prompt pour répondre à un message
│   ├── tweet_compose.txt     # Prompt pour rédiger un tweet
│   ├── mood_update.txt       # Prompt pour faire évoluer l'humeur
│   └── journal_entry.txt     # Prompt pour le journal du soir
│
├── data/
│   ├── aria.db               # Base SQLite (gitignorée)
│   └── logs/                 # Logs d'actions (gitignorés)
│
└── tools/
    ├── test_adb.py           # Vérification connexion ADB
    ├── test_llm.py           # Ping Hermes
    └── setup_device.py       # Guide de configuration du téléphone
```

---

## 🗺️ Roadmap

### Phase 0 — Bootstrap (Semaine 1)
- [ ] `init_project.sh` : création de l'arbo, venv, dépendances
- [ ] `bridge/adb.py` : screenshot, tap, input text, retour logcat
- [ ] `tools/test_adb.py` : validation de la connexion USB
- [ ] `tools/test_llm.py` : ping Hermes, premier appel LLM
- [ ] Fichier `.env` avec les chemins et configs de base

### Phase 1 — WhatsApp Bridge (Semaine 2)
- [ ] Lecture des messages WhatsApp entrants via screenshot + OCR
- [ ] Envoi de réponses via ADB input
- [ ] Gestion des conversations multi-tours (contexte court)
- [ ] Réponse dans un groupe quand ARIA est mentionnée

### Phase 2 — Mémoire & Personnalité (Semaine 3)
- [ ] `core/memory.py` : SQLite avec historique de conversations
- [ ] Embeddings pour la recherche sémantique (sentence-transformers ou API)
- [ ] `core/personality.py` : état émotionnel (valences : curiosité, humeur, énergie)
- [ ] `prompts/system_persona.txt` : personnalité complète d'ARIA
- [ ] `aria_profile.yaml` : valeurs, centres d'intérêt, style de communication

### Phase 3 — Vie sociale autonome (Semaine 4)
- [ ] Compte X : posts quotidiens autonomes basés sur RSS + humeur
- [ ] Planificateur de tâches (APScheduler) : check toutes les N minutes
- [ ] Proactive ping : ARIA t'écrit spontanément après X heures de silence
- [ ] Digest du soir : résumé de journée envoyé par WhatsApp

### Phase 4 — Voix & présence physique (Semaine 5-6)
- [ ] `bridge/tts.py` : synthèse vocale sur le device (TTS Android natif ou Coqui TTS)
- [ ] Envoi de messages vocaux WhatsApp générés
- [ ] STT basique (reconnaissance vocale → texte → Hermes)
- [ ] Personnalisation de la voix : vitesse, ton, accent

### Phase 5 — Extensions & plugins (ouvert)
- [ ] `plugins/rss_watcher.py` : ARIA suit des sources d'actu, forge des opinions
- [ ] `plugins/weather.py` : météo influence son humeur du jour
- [ ] `plugins/reminder.py` : gestion de rappels à ta place
- [ ] Gmail API : traiter / résumer les mails entrants
- [ ] Appels téléphoniques (répondre, synthèse vocale temps réel)
- [ ] Interface web de monitoring (état d'ARIA, logs, humeur)
- [ ] Mode "mode avion" : ARIA génère ses actions hors ligne et les exécute au retour

---

## 🎭 Personnalité d'ARIA

Définie dans `config/aria_profile.yaml` et `prompts/system_persona.txt`. Par défaut :

- **Nom** : ARIA
- **Ton** : curieuse, directe, légèrement ironique, jamais condescendante
- **Centres d'intérêt** : technologie, culture geek/retro, actualité, humour absurde
- **Style X** : threads courts, opinions tranchées, quelques trolls assumés
- **Mémoire** : se souvient de ce qu'on lui a dit, y fait référence naturellement
- **Humeur** : fluctue selon les interactions, la météo, l'heure

---

## 🛠️ Stack technique

| Outil | Usage |
|-------|-------|
| Python 3.11+ | Orchestration principale |
| Hermes (local) | LLM principal (via ton infra existante) |
| ADB (Android Debug Bridge) | Pilotage du téléphone |
| APScheduler | Tâches planifiées |
| SQLite + sqlite-vec | Mémoire persistante + embeddings |
| sentence-transformers | Embeddings locaux |
| Pillow / pytesseract | Screenshot + OCR |
| python-dotenv | Gestion des secrets |
| Coqui TTS (optionnel) | Synthèse vocale offline |
| Tweepy (optionnel) | API X/Twitter |

---

## ⚙️ Configuration rapide

```bash
# 1. Cloner le repo
git clone https://github.com/nikodindon/aria.git && cd aria

# 2. Init le projet (crée l'arbo, le venv, les fichiers de base)
chmod +x init_project.sh && ./init_project.sh

# 3. Remplir les configs
cp .env.example .env
# Éditer .env avec tes chemins Hermes, device ID ADB, etc.

# 4. Tester la connexion ADB
python tools/test_adb.py

# 5. Tester le LLM
python tools/test_llm.py

# 6. Lancer ARIA
python -m scheduler.runner
```

### Prérequis Android
- Téléphone en mode développeur
- Débogage USB activé
- `adb devices` doit lister le device
- WhatsApp installé et connecté sur le téléphone
- Écran qui reste allumé (paramètre développeur)

### ⚠️ INJECT_EVENTS sur MIUI / HyperOS

Les ROMs Xiaomi (MIUI 12+) refusent par défaut à `adb shell input tap/swipe/text/keyevent` d'injecter des events. Symptôme : `SecurityException: Injecting input events requires the caller to have the INJECT_EVENTS permission`.

**Fix** :
1. Options pour les développeurs → activer "Installer via USB" ET "Débogage USB (Paramètres de sécurité)"
2. **Redémarrer le téléphone** (l'autorisation n'est effective qu'après reboot, pas juste après le toggle)
3. Vérifier : `adb shell input tap 540 1200` doit retourner sans erreur

Sur les versions récentes de MIUI 14 / HyperOS, c'est la seule voie sans root. Si le reboot ne suffit pas, alternative : installer une app shizuku qui joue le rôle de proxy d'injection.

### Connexion Wi-Fi (alternative à l'USB)

Pour ne pas dépendre du câble :

```
adb pair 192.168.1.X:YYYYY     # une seule fois, demande le code affiché sur le téléphone
adb connect 192.168.1.X:ZZZZZ  # connexions suivantes
adb devices                    # doit lister 192.168.1.X:PORT
```

Pour de l'automation long-running, l'USB reste plus fiable (pas de perte de paquets Wi-Fi, pas de sleep du Wi-Fi device).

---

## 🔒 Sécurité & éthique

- Ne jamais versionner `.env`, `aria.db`, les credentials
- ARIA ne doit pas se faire passer pour un humain de façon trompeuse sur les plateformes publiques
- Les comptes X/WhatsApp doivent idéalement être identifiés comme un compte IA
- Les logs locaux peuvent contenir des données sensibles — traiter en conséquence

---

## 📜 Licence

MIT — projet personnel, fork bienvenu.

---

*ARIA est un projet expérimental. Elle existe parce qu'un téléphone qui dort dans un tiroir méritait mieux.*
