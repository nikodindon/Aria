# 📱 ARIA — Autonomous Roaming Intelligence Agent

> Une IA avec une vraie vie numérique, pilotée depuis ton PC via ADB.

ARIA est un compagnon IA autonome qui vit dans un téléphone Android dédié. Elle a sa propre personnalité persistante, sa propre voix, et elle pilote le téléphone comme un humain (WhatsApp, YouTube, apps). Pas un chatbot : une entité numérique avec une présence physique.

---

## 🧠 Concept

ARIA n'attend pas qu'on lui parle. Elle :
- Répond à tes messages WhatsApp avec contexte, mémoire long-terme, et **recherche web** via Hermes
- Délègue intelligemment à un agent helper (Hermes) pour les questions d'actu / facts
- Pilote le téléphone : ouvre WhatsApp, tape des messages, ouvre d'autres apps (YouTube, etc.)
- Se réveille quand le tel est endormi, s'endort après avoir envoyé un message
- Dédup les notifs Android (y compris tronquées) pour éviter le spam
- Auto-restart via daemon + service systemd ready

Le cerveau : **Hermes** (ton agent CLI), qui peut faire de la recherche web. Le téléphone est l'interface physique vers le monde.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                    TON PC (Linux Mint)               │
│                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌───────────┐  │
│  │  Hermes  │◄──►│  Orchestrat. │◄──►│  Mémoire  │  │
│  │   CLI    │    │  (Python)    │    │ (SQLite)  │  │
│  └──────────┘    └──────┬───────┘    └───────────┘  │
│                         │                           │
│                    ADB Bridge (Wi-Fi ou USB)        │
└─────────────────────────┼───────────────────────────┘
                          │ adb (192.168.1.16:41199)
┌─────────────────────────▼───────────────────────────┐
│                TÉLÉPHONE ANDROID                     │
│   WhatsApp │ YouTube │ Maps │ n'importe quelle app  │
└─────────────────────────────────────────────────────┘
```

### Composants principaux

| Module | Rôle |
|--------|------|
| `core/memory.py` | SQLite (messages, journal, mood, knowledge, **users**, **reminders**, **messages_fts** FTS5) |
| `core/context_builder.py` | Assemblage du system prompt (persona + mood + news + météo + FTS5 recall) |
| `bridge/adb.py` | Wrapper ADB (tap, swipe, screenshot, input text, raw shell, open_app) |
| `bridge/whatsapp.py` | Lire/envoyer des messages WhatsApp (UI Automator + deep link + **wakeup/sleep**) |
| `bridge/tts.py` | Synthèse vocale offline (spd-say + espeak-ng) |
| `plugins/agent_delegate.py` | **Délégation à Hermes** (`hermes chat -q <query>`) avec extraction de réponse |
| `plugins/rss_watcher.py` | Flux RSS (Hacker News par défaut) pour contexte d'actu |
| `plugins/weather.py` | Météo via wttr.in |
| `plugins/reminder.py` | Système de rappels (CRUD SQLite) |
| `tools/aria_loop.py` | Gateway : poll notifs → **delegate Hermes** → deep link + dedup + sleep |
| `tools/aria_daemon.py` | Daemon avec auto-restart infini (wrap aria_loop) |
| `tools/aria.service.example` | Unit systemd pour auto-start au boot |
| `tools/aria_pair.py` | CLI d'appairage user |
| `tools/aria_plugins.py` | CLI unifié pour news/weather/reminder |
| `tools/aria_speak.py` | CLI TTS |
| `tests/level1.py` | Suite de 22 tests unitaires/intégration/sécurité/régression |

---

## 📁 Structure du projet

```
aria/
├── README.md
├── .gitignore
├── requirements.txt
│
├── core/
│   ├── memory.py             # SQLite (tables + FTS5 + redact_credentials)
│   ├── context_builder.py    # system prompt (historique + FTS5 + news + météo)
│   ├── brain.py              # wrapper chat (legacy, peu utilisé)
│   └── personality.py        # mood, persona
│
├── bridge/
│   ├── adb.py                # Primitives ADB (tap, swipe, screenshot, open_app)
│   ├── whatsapp.py           # UI Automator + deep link + wakeup/sleep
│   └── tts.py                # spd-say + espeak-ng (offline FR)
│
├── plugins/
│   ├── agent_delegate.py     # **Délégation à Hermes** (subprocess hermes chat -q)
│   ├── rss_watcher.py        # RSS feed aggregator
│   ├── weather.py            # wttr.in wrapper
│   └── reminder.py           # rappels SQLite
│
├── prompts/
│   └── whatsapp_reply.txt    # system prompt WhatsApp
│
├── scheduler/                # stub pour Phase scheduler (legacy)
│
├── data/                     # gitignoré
│   ├── aria.db               # SQLite (users, messages, mood, knowledge, reminders, messages_fts)
│   ├── seen_texts.json       # dédup window 10 min
│   └── seen_texts.lock       # lock fichier pour dédup
│
└── tools/
    ├── aria_pair.py          # CLI appairage
    ├── aria_loop.py          # **gateway principal** (poll → delegate Hermes → send)
    ├── aria_daemon.py        # daemon auto-restart
    ├── aria.service.example  # unit systemd
    ├── aria_speak.py         # CLI TTS
    ├── aria_plugins.py       # CLI news/weather/reminder
    ├── test_*.py             # tests legacy
    └── ...

└── tests/
    └── level1.py             # 22 tests canoniques
```

---

## 🗺️ Roadmap

### Phase 0 — Bootstrap ✅ FAIT
- [x] `init_project.sh` : arbo + venv + deps
- [x] `bridge/adb.py` : primitives ADB
- [x] Bugfixes critiques : system prompt + memory init lazy

### Phase 1 — WhatsApp Bridge ✅ FAIT
- [x] `bridge/whatsapp.py` : lecture via UI Automator + deep link pour l'envoi
- [x] `redact_credentials()` : masque codes 4-8 chiffres (OTP, etc.)
- [x] `send_message()` : envoi via deep link `wa.me/<phone>?text=` (accents préservés)
- [x] `tools/aria_reply_demo.py` : end-to-end READ → WRITE

### Phase 2 — Gateway WhatsApp ✅ FAIT
- [x] Table `users` dans `core/memory.py`
- [x] `tools/aria_pair.py` : CLI appairage user
- [x] `tools/aria_loop.py` : polling `dumpsys notification` → dispatch
- [x] Détection des notifs WhatsApp, extraction numéro, match user
- [x] **Dedup temporel** : `data/seen_texts.json` + lock fichier `data/seen_texts.lock`
- [x] **Match par nom** si la notif n'a pas de numéro (contact reconnu)
- [x] **Wakeup + unlock** du téléphone avant envoi (KEYCODE_WAKEUP + swipe)
- [x] **Sleep après envoi** (KEYCODE_SLEEP) pour que la prochaine notif soit pushée

### Phase 2+3 — Mémoire long-terme ✅ FAIT
- [x] Table `messages_fts` (FTS5 virtual) + 3 triggers (ai/ad/au) pour indexation auto
- [x] `recall_relevant(query, k=3)` : recherche full-text avec sanitize regex + format OR
- [x] Intégration dans `core/context_builder.py` : section `{relevant}` dans le system prompt

### Phase 4 — TTS ✅ FAIT
- [x] `bridge/tts.py` : `speak()` via spd-say + espeak-ng (offline FR)
- [x] `tools/aria_speak.py` : CLI `--voice`, `--language`, `--rate`

### Phase 5 — Scheduler tasks ✅ FAIT
- [x] `scheduler/tasks/evening_digest.py` : journal du soir envoyé via WhatsApp
- [x] `scheduler/tasks/proactive_ping.py` : silence > 48h → message spontané

### Phase 6 — Plugins ✅ FAIT
- [x] `plugins/rss_watcher.py` : Hacker News par défaut, 30 news stockées en DB
- [x] `plugins/weather.py` : wttr.in JSON, fallback gracieux
- [x] `plugins/reminder.py` : CRUD rappels
- [x] Intégration dans le system prompt (sections `{news}` et `{weather}`)

### Phase 7 — Délégation web via Hermes ✅ FAIT
- [x] `plugins/agent_delegate.py` : subprocess `hermes chat -q <query>` avec extraction de la réponse
- [x] Intégration dans `reply_to_user` : **TOUT est délégué à Hermes** (pas de LLM local rate-limité)
- [x] Contexte WhatsApp (historique + FTS5 + news + météo) envoyé en préfixe
- [x] Délai 6-20s (vs 30s-2min avec LLM local)

### Phase 8 — Robustesse ✅ FAIT
- [x] Daemon avec auto-restart infini (`tools/aria_daemon.py`)
- [x] Service systemd ready (`tools/aria.service.example`)
- [x] Suite de tests Level 1 : 22 tests (unit/intégration/sécurité/régression) dans `tests/level1.py`
- [x] **Dedup exact + préfixe 40 chars** (gère les notifs Android tronquées au milieu)
- [x] **Troncature des réponses > 700 chars** (évite tap rate sur le bouton Envoyer)
- [x] **Fallback gracieux** si LLM/Hermes échoue (message d'erreur amical au lieu de silence)

### Phase 9 — Pilotage d'autres apps ✅ EN COURS
- [x] `plugins/app_actions.py` : catalogue d'actions physiques (open_app, open_url, open_youtube_search)
- [x] Format `[ACTION] name|args` parsé par ARIA et exécuté via ADB
- [x] System prompt explique à Hermes les actions disponibles
- [ ] Catalogue étendu : Maps avec itinéraire, Gmail avec recherche, etc.
- [ ] Actions imbriquées : "ouvre YouTube, cherche 'tutos Python', lis la 1re vidéo"
- [ ] Catalogue d'actions spécifiques par app (ex: `youtube_play_first_result`)

### Phase 9b — Intentions (au lieu d'actions) 🔵 REFACTOR
- [ ] Couche d'abstraction : LLM exprime une **intention** (open_video_player, get_route, send_email)
- [ ] Planificateur Python choisit le plugin (YouTube vs NewPipe, Maps vs Organic Maps)
- [ ] Permet de switcher d'app sans modifier le prompt du LLM
- [ ] `plugins/intentions.py` : registre intention → plugins disponibles

### Phase 10 — Recherche sémantique hybride 🔵 À VENIR
- [ ] Embeddings locaux (sentence-transformers déjà installé)
- [ ] `core/memory.py` : table `messages_embeddings` (id, vector_blob)
- [ ] `recall_relevant_hybrid(query)` : combine FTS5 + cosine similarity
- [ ] Re-rank des résultats FTS5 par proximité sémantique
- [ ] Remplacement progressif du recall FTS5 par le hybrid

### Phase 11 — Appels téléphoniques 🔵 À VENIR
- [ ] Détection appels entrants via `dumpsys telephony` ou notif
- [ ] Décrocher / raccrocher via ADB (`KEYCODE_CALL` / `am start ANSWER_PHONE`)
- [ ] Capturer audio micro via `screenrecord` ou app tierce
- [ ] STT streaming (Whisper local ou API)
- [ ] TTS temps réel (Piper / Coqui) pour répondre
- [ ] Appels sortants sur demande (`am start CALL tel:...`)
- [ ] VAD (Voice Activity Detection) pour demi-duplex naturel

### Phase 12 — Mémoire épisodique + carnet relationnel 🔵 TRANSFORMATEUR
- [ ] `core/memory.py` : table `episodes` (date, summary, people, topics, mood_at_time)
- [ ] Consolidation automatique : tous les X messages, on résume la journée
- [ ] `core/people.py` : table `people` (name, likes, dislikes, notes, last_topic)
- [ ] Pour chaque user appairé, ARIA construit un carnet relationnel
- [ ] Récupération de contexte : "tu te souviens quand on a parlé de X ?"
- [ ] `core/curiosity.py` : centres d'intérêt évolutifs (fréquence de mentions de topics)

### Phase 13 — Humeur riche + cycle circadien 🔵 VIE NUMÉRIQUE
- [ ] Humeur multi-dim : `curiosity`, `energy`, `irony`, `motivation`, `nostalgia`, `focus`, `dreaminess`
- [ ] `core/circadian.py` : cycle selon heure/jour/semaine (8h bonne humeur, 2h fatiguée, dimanche bavarde)
- [ ] Style de réponse influencé par l'humeur (phrases courtes si fatiguée, plus bavard si curieuse)
- [ ] `core/monologue.py` : journal intime jamais envoyé, juste pour elle

### Phase 14 — Planification + objectifs long-terme 🔵 AGENT AUTONOME
- [ ] `core/goals.py` : table `goals` (description, status, plan, sub_goals, due_at)
- [ ] ARIA peut créer un goal : "trouve un nouveau jeu pour Niko" sur 3 jours
- [ ] Planificateur : goal → sous-objectifs → actions → résultat → réflexion
- [ ] `scheduler/tasks/goal_runner.py` : vérifie les goals actifs périodiquement
- [ ] Veille proactive : "j'ai vu passer un truc qui pourrait t'intéresser" via Hacker News + centres d'intérêt

### Phase 15 — Caméra + vision 🔵 VISION
- [ ] Capture photo/vidéo périodique via ADB (`screencap` + `screenrecord`)
- [ ] Modèle vision (LLaVA, Moondream) pour comprendre la scène
- [ ] Mémoire visuelle : ARIA se souvient de ce qu'elle "voit"
- [ ] Proactivité visuelle : "il fait sombre dans le salon, allume la lumière ?"

### Phase 16 — Multi-devices (swarm) 🔵 ARMÉE
- [ ] `tools/aria_orchestrator.py` : pilote N devices en parallèle
- [ ] Chaque agent a sa DB locale (préfixe `device_id`)
- [ ] Communication inter-agents via MQTT local ou groupe WhatsApp dédié
- [ ] Spécialités par agent : Aria-Caméra, Aria-Son, Aria-GPS, Aria-Sécurité
- [ ] Cas d'usage : surveillance multi-pièces, monitoring environnemental

### Phase 17 — Web UI monitoring 🔵 VISIBILITÉ
- [ ] FastAPI + HTMX (ou Streamlit) en local
- [ ] Dashboard : humeur, derniers messages, logs en temps réel
- [ ] **Observabilité** : métriques (temps réponse, actions, erreurs ADB, redémarrages)
- [ ] **Journal d'événements** : séparation conversations vs événements système
- [ ] Déclencher des actions manuellement (test rapide sans WhatsApp)
- [ ] Mode "vie" : voir plusieurs agents sur une carte (multi-devices)

### Phase 18 — Compétences installables + sécurité par niveaux 🔵 OUVERTURE
- [ ] Système `aria install <plugin>` : ajoute un plugin (prompts, outils, mémoire)
- [ ] **Niveaux de confiance** : READ_ONLY, BENIGN, SENSITIVE (avec confirmation)
- [ ] Appels et apps bancaires toujours en SENSITIVE
- [ ] **File d'attente persistante** : actions rejouables après crash ADB
- [ ] `plugins/camera.py`, `plugins/spotify.py`, `plugins/calendar.py`, `plugins/homeassistant.py`

### Phase 19 — À venir 🔵
- [ ] Notifications multi-users / groupes WhatsApp
- [ ] Réactions (emojis) + messages vocaux via TTS occasionnels
- [ ] Sécurité élargie (mots de passe redact en plus des OTP)
- [ ] Mode "avion" : génère ses actions hors ligne, exécute au retour
- [ ] Migration `list_conversations` + `open_conversation` vers UI Automator
- [ ] ARIA qui "découvre" les interfaces (voir écran → comprendre → cliquer) sans connaître l'app
- [ ] **Robotique low-cost** : smartphones fixés sur châssis à roues (swarm robotics)

---

## 🎭 Personnalité d'ARIA

Définie dans `prompts/whatsapp_reply.txt` et `core/context_builder.py` :
- **Nom** : ARIA
- **Ton** : curieuse, directe, légèrement ironique, jamais condescandante
- **Centres d'intérêt** : technologie, culture geek/retro, actualité, humour absurde
- **Style WhatsApp** : messages courts (1-3 phrases, max 700 chars), familier, pas de formule de politesse
- **Mémoire** : se souvient via FTS5, fait référence naturellement aux anciens messages
- **Humeur** : fluctue selon les interactions, la météo, l'heure

---

## 🛠️ Stack technique

| Outil | Usage |
|-------|-------|
| Python 3.11+ | Orchestration principale |
| **Hermes CLI** | **LLM principal** (recherche web intégrée, pas de rate limit) |
| ADB (Android Debug Bridge) | Pilotage du téléphone (Wi-Fi ou USB) |
| SQLite + FTS5 | Mémoire persistante (users, messages, mood, knowledge, reminders, **recherche full-text**) |
| APScheduler | Tâches planifiées (Phase 5) |
| `hermes` (subprocess) | Agent helper pour les questions d'actu (via plugin `agent_delegate.py`) |
| python-dotenv | Gestion des secrets |

---

## ⚙️ Configuration rapide

```bash
# 1. Cloner le repo
git clone https://github.com/nikodindon/Aria.git && cd Aria

# 2. Init le projet
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Vérifier ADB
adb devices
# Doit lister 192.168.1.16:41199 (ou autre device)

# 4. Vérifier Hermes
which hermes
hermes chat -q "Salut, dis juste 'ok'"
# Doit répondre "ok" en 5-10s

# 5. Appairer un user WhatsApp
python tools/aria_pair.py --phone 33617186267 --name "Niko"

# 6. Lancer le daemon (gateway permanent)
python tools/aria_daemon.py --interval 5
# Le daemon poll les notifs toutes les 5s et y répond via Hermes

# 7. (optionnel) Tests
python tests/level1.py
# Doit afficher 22/22 passed
```

### Prérequis Android
- Téléphone en mode développeur
- Débogage USB activé
- `adb devices` doit lister le device
- WhatsApp installé et connecté sur le téléphone (compte dédié à ARIA)
- **Écran qui s'éteint** : ARIA le réveille avec KEYCODE_WAKEUP avant d'envoyer

### Connexion Wi-Fi (alternative à USB)

```bash
adb pair 192.168.1.X:YYYYY     # une seule fois
adb connect 192.168.1.X:ZZZZZ  # connexions suivantes
```

---

## 🤖 Le gateway : pairing + loop

ARIA fonctionne comme un bot, mais **en local** (pas de cloud, pas d'API tierce, pas de Twilio).

### Le flow

```
Toi (tel perso)         ARIA gateway (PC)              Xiaomi (num dédié)
+33 6 17 18 62 67                                     +33 7 80 85 81 36
       │                       │                              │
       │  message WhatsApp     │                              │
       │ ──────────────────────┼─────────────────────────────►│
       │                       │                              │
       │                       │ ◄─ dumpsys notification      │
       │                       │    parse → extract phone     │
       │                       │    match user Niko           │
       │                       │    recall FTS5 (long-terme)  │
       │                       │    delegate Hermes (actu)    │
       │                       │    send via wa.me deep link  │
       │                       │ ────────────────────────────►│
       │                       │                              │
       │                       │  KEYCODE_SLEEP (endort tel)  │
       │                       │                              │
       │ ◄─────────────────────┼──────────────────────────────│
       │  reponse WhatsApp     │                              │
```

### Boucle gateway

```bash
# Manuel (foreground, Ctrl+C pour arreter)
python tools/aria_loop.py --interval 5

# Daemon (auto-restart infini, 5s poll)
python tools/aria_daemon.py --interval 5

# Production (systemd, auto-start au boot)
sudo cp tools/aria.service.example /etc/systemd/system/aria.service
sudo systemctl daemon-reload
sudo systemctl enable --now aria.service
```

La boucle :
1. Lance `dumpsys notification --noredact`
2. Filtre les notifs `pkg=com.whatsapp`
3. Extrait le numéro OU matche par nom (pour les contacts reconnus)
4. **Dedup exact + préfixe 40 chars** (gère notifs Android tronquées)
5. **Lock fichier** sur le dedup (sérialise les polls concurrents)
6. Construit le contexte : historique + FTS5 recall + news + météo
7. Délègue à **Hermes** (`hermes chat -q`) qui fait la recherche web si besoin
8. Tronque la réponse à 700 chars (évite tap rate sur Envoyer)
9. Envoie via deep link `https://wa.me/<phone>?text=<message>`
10. **Wakeup** le téléphone (KEYCODE_WAKEUP + swipe unlock)
11. **Send** via deep link + tap sur le bouton Envoyer
12. **Sleep** le téléphone (KEYCODE_SLEEP) pour que la prochaine notif soit pushée
13. Log en DB (entrée `messages` + `last_seen` du user)

---

## 🐛 Limites connues & bugs latents

- **`list_conversations` et `open_conversation` toujours sur OCR** : à migrer vers UI Automator
- **Le bouton Envoyer change de position** si le message est très long (mitigé par troncature 700 chars)
- **`press_back()` sur MIUI quitte la conversation** : ne pas l'utiliser pour fermer le clavier
- **LLM local (LiteLLM) abandonné** : trop rate-limité. ARIA utilise maintenant **Hermes** comme seul LLM
- **Hermes a une latence de 5-20s** par message (acceptable pour la plupart des cas)
- **Pas de gestion d'erreur réseau** : si le téléphone perd le Wi-Fi, le daemon peut crasher. À wrapper dans un retry (en cours)

---

## 🔒 Sécurité & éthique

- Ne jamais versionner `.env`, `data/aria.db`, `data/seen_texts.json`, les credentials
- ARIA ne doit pas se faire passer pour un humain de façon trompeuse
- Les comptes WhatsApp doivent idéalement être identifiés comme un compte IA
- `redact_credentials()` masque les codes à 4-8 chiffres (OTP, etc.) dans tout ce qui est loggé
- **Le dédup + lock fichier** empêche ARIA d'envoyer 2 fois le même message (anti-spam)

---

## 📜 Licence

MIT — projet personnel, fork bienvenu.

---

*ARIA est un projet expérimental. Elle existe parce qu'un téléphone qui dort dans un tiroir méritait mieux.*
