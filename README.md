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

Le cerveau tourne sur ton PC (Linux Mint + LiteLLM). Le téléphone est l'interface physique vers le monde.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                    TON PC (Linux Mint)               │
│                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌───────────┐  │
│  │  LiteLLM │◄──►│  Orchestrat. │◄──►│  Mémoire  │  │
│  │  (LLM)   │    │  (Python)    │    │ (SQLite)  │  │
│  └──────────┘    └──────┬───────┘    └───────────┘  │
│                         │                           │
│                    ADB Bridge (Wi-Fi ou USB)        │
└─────────────────────────┼───────────────────────────┘
                          │ adb (192.168.1.X:PORT)
┌─────────────────────────▼───────────────────────────┐
│                  TÉLÉPHONE ANDROID                   │
│   WhatsApp (numéro dédié) │ X (Twitter) │ TTS / Micro│
└─────────────────────────────────────────────────────┘
```

### Composants principaux

| Module | Rôle |
|--------|------|
| `core/brain.py` | Interface LLM via LiteLLM (multi-provider) |
| `core/memory.py` | Mémoire long-terme SQLite (messages, journal, mood, knowledge, **users**) |
| `core/personality.py` | État émotionnel, humeur, journal intime |
| `core/context_builder.py` | Assemblage du system prompt (persona + mood + contexte) |
| `bridge/adb.py` | Wrapper ADB (tap, swipe, screenshot, input text, raw shell) |
| `bridge/whatsapp.py` | Lire/envoyer des messages WhatsApp (UI Automator + deep link) |
| `bridge/twitter.py` | Poster, répondre, suivre des fils (stub) |
| `bridge/tts.py` | Synthèse vocale (stub) |
| `tools/aria_pair.py` | CLI d'appairage d'un user (gateway) |
| `tools/aria_loop.py` | Boucle gateway : poll notifs → dispatch vers LLM → réponse auto |
| `tools/aria_reply_demo.py` | Démonstration end-to-end du pipeline de réponse |
| `tools/test_*` | Scripts de validation manuelle |

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
│   └── schedule.yaml         # Fréquence des actions autonomes
│
├── core/
│   ├── __init__.py
│   ├── brain.py              # Appels LLM via LiteLLM
│   ├── memory.py             # SQLite (messages, journal, mood, knowledge, users)
│   ├── personality.py        # Humeur, état émotionnel, journal
│   └── context_builder.py    # Assemble le contexte avant chaque appel LLM
│
├── bridge/
│   ├── __init__.py
│   ├── adb.py                # Primitives ADB (tap, swipe, screenshot, input text)
│   ├── whatsapp.py           # READ via UI Automator + OCR fallback, WRITE via deep link
│   ├── twitter.py            # Stub (Phase 3)
│   └── tts.py                # Stub (Phase 4)
│
├── scheduler/
│   ├── __init__.py
│   ├── runner.py             # Boucle principale (APScheduler, stub)
│   └── tasks/
│       ├── check_messages.py # Polling WhatsApp/mail (stub)
│       ├── daily_post.py     # Post X autonome (stub)
│       ├── evening_digest.py # Journal + résumé de journée (stub)
│       └── proactive_ping.py # ARIA t'écrit en premier (stub)
│
├── data/                     # DB SQLite (gitignorée)
│   ├── aria.db
│   └── logs/
│
└── tools/
    ├── aria_pair.py          # CLI d'appairage
    ├── aria_loop.py          # Boucle gateway
    ├── aria_reply_demo.py    # Démonstration end-to-end
    ├── setup_device.py       # Guide de configuration du téléphone
    ├── test_adb.py           # Validation connexion ADB
    ├── test_adb_primitives.py# Test des primitives ADB
    ├── test_llm.py           # Ping LLM
    ├── test_persona.py       # Test de la personnalité
    └── test_whatsapp_list.py # Test de list_conversations
```

---

## 🗺️ Roadmap

### Phase 0 — Bootstrap ✅ FAIT
- [x] `init_project.sh` : création de l'arbo, venv, dépendances
- [x] `bridge/adb.py` : screenshot, tap, input text, raw shell
- [x] `tools/test_adb.py` : validation de la connexion ADB
- [x] `tools/test_llm.py` : ping LLM, premier appel
- [x] Fichier `.env` avec les chemins et configs de base
- [x] Bugfixes critiques : system prompt + memory init lazy

### Phase 1 — WhatsApp Bridge ✅ FAIT
- [x] `bridge/whatsapp.py` : lecture messages via **UI Automator** (rapide, sans OCR) + OCR fallback
- [x] `redact_credentials()` : masque les codes 4-8 chiffres dans les messages loggés
- [x] `current_view()` : heuristique pour détecter la vue courante (discussions / conversation)
- [x] `list_conversations()` : liste des conversations (vue Discussions)
- [x] `open_conversation()` : ouverture d'une conv par nom
- [x] `read_conversation()` : lecture des messages d'une conv (direction + text)
- [x] `send_message()` : envoi via **deep link `wa.me/<phone>?text=`** (voie préférée) ou tap-based (fallback)
- [x] `tools/aria_reply_demo.py` : pipeline end-to-end READ → LLM → WRITE

### Phase 2 — Gateway WhatsApp ✅ FAIT
- [x] Table `users` dans `core/memory.py` (phone, name, paired_at, last_seen, notes)
- [x] `tools/aria_pair.py` : CLI d'appairage
- [x] `tools/aria_loop.py` : polling `dumpsys notification` → dispatch
  - Détection des notifs WhatsApp entrantes
  - Extraction du numéro de l'expéditeur (formats international +33 et national 0X)
  - Match avec les users appairés (matching sur 9 derniers chiffres)
  - Génération de réponse via LLM avec system persona
  - Envoi via deep link
  - Log en DB (messages + mood touch)
- [x] Déduplication des notifs (diff entre poll précédent et poll actuel)

### Phase 3 — Mémoire & Personnalité (en cours)
- [x] `core/memory.py` : SQLite avec historique de conversations
- [x] `core/personality.py` : état émotionnel (mood, energy, curiosity)
- [x] `core/context_builder.py` : assemblage du system prompt
- [x] `aria_profile.yaml` : valeurs, centres d'intérêt, style de communication
- [ ] Embeddings pour la recherche sémantique (sentence-transformers, installé mais pas câblé)
- [ ] Recherche dans la mémoire des anciens messages avant de répondre

### Phase 4 — Vie sociale autonome (à venir)
- [ ] Compte X : posts quotidiens autonomes basés sur RSS + humeur
- [ ] Planificateur de tâches (APScheduler) : check toutes les N minutes
- [ ] Proactive ping : ARIA t'écrit spontanément après X heures de silence
- [ ] Digest du soir : résumé de journée envoyé par WhatsApp
- [ ] Migration de `list_conversations` + `open_conversation` vers UI Automator

### Phase 5 — Voix & présence physique (à venir)
- [ ] `bridge/tts.py` : synthèse vocale sur le device
- [ ] Envoi de messages vocaux WhatsApp générés
- [ ] STT basique (reconnaissance vocale → texte → LLM)
- [ ] Personnalisation de la voix : vitesse, ton, accent

### Phase 6 — Extensions & plugins (ouvert)
- [ ] `plugins/rss_watcher.py` : ARIA suit des sources d'actu, forge des opinions
- [ ] `plugins/weather.py` : météo influence son humeur du jour
- [ ] `plugins/reminder.py` : gestion de rappels à ta place
- [ ] Gmail API : traiter / résumer les mails entrants
- [ ] Appels téléphoniques (répondre, synthèse vocale temps réel)
- [ ] Interface web de monitoring (état d'ARIA, logs, humeur)
- [ ] Mode "mode avion" : ARIA génère ses actions hors ligne et les exécute au retour

---

## 🎭 Personnalité d'ARIA

Définie dans `config/aria_profile.yaml` et `core/context_builder.py`. Par défaut :
- **Nom** : ARIA
- **Ton** : curieuse, directe, légèrement ironique, jamais condescendante
- **Centres d'intérêt** : technologie, culture geek/retro, actualité, humour absurde
- **Style WhatsApp** : messages courts (2-3 phrases), familier, pas de formule de politesse
- **Mémoire** : se souvient de ce qu'on lui a dit, y fait référence naturellement
- **Humeur** : fluctue selon les interactions, la météo, l'heure

---

## 🛠️ Stack technique

| Outil | Usage |
|-------|-------|
| Python 3.11+ | Orchestration principale |
| LiteLLM (local) | LLM principal (via ton infra existante : llama.cpp server, OpenRouter, etc.) |
| ADB (Android Debug Bridge) | Pilotage du téléphone (USB ou Wi-Fi) |
| APScheduler | Tâches planifiées (Phase 4) |
| SQLite | Mémoire persistante (users, messages, journal, mood, knowledge) |
| sentence-transformers | Embeddings locaux (installé, à câbler) |
| Pillow / pytesseract | Screenshot + OCR (fallback uniquement) |
| python-dotenv | Gestion des secrets |

---

## ⚙️ Configuration rapide

```bash
# 1. Cloner le repo
git clone https://github.com/nikodindon/aria.git && cd aria

# 2. Init le projet (crée l'arbo, le venv, les fichiers de base)
chmod +x init_project.sh && ./init_project.sh

# 3. Remplir les configs
cp .env.example .env
# Éditer .env avec tes chemins LLM, device ID ADB, etc.

# 4. Tester la connexion ADB
python tools/test_adb.py

# 5. Tester le LLM
python tools/test_llm.py

# 6. Appairer un user WhatsApp
python tools/aria_pair.py --phone 33617186267 --name "Niko"

# 7. Lancer le gateway
python tools/aria_loop.py --interval 30
```

### Prérequis Android
- Téléphone en mode développeur
- Débogage USB activé
- `adb devices` doit lister le device
- WhatsApp installé et connecté sur le téléphone (compte dédié à ARIA)
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

## 🤖 Le gateway : pairing + loop

ARIA fonctionne comme un bot Telegram-like, mais **en local** (pas de cloud, pas d'API tierce, pas de Twilio).

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
       │                       │    LLM.generate(response)    │
       │                       │    send via wa.me deep link  │
       │                       │ ────────────────────────────►│
       │                       │                              │
       │ ◄─────────────────────┼──────────────────────────────│
       │  reponse WhatsApp     │                              │
```

### Appairage

```bash
python tools/aria_pair.py --phone 33617186267 --name "Niko"
```

Cela enregistre le user dans la table `users` de la DB SQLite (`data/aria.db`). À partir de là, ARIA reconnaît les messages de ce numéro et peut y répondre.

L'appairage est idempotent : relancer la commande ne crée pas de doublon, ça met à jour le `name` ou les `notes`.

### Boucle gateway

```bash
python tools/aria_loop.py --interval 30   # poll toutes les 30s
python tools/aria_loop.py --interval 5    # plus réactif
python tools/aria_loop.py --once          # une seule itération (debug)
```

La boucle :
1. Lance `dumpsys notification --noredact` (zéro screenshot, instantané)
2. Filtre les notifs `pkg=com.whatsapp`
3. Extrait le numéro du `android.title` (formats `+33 6 17 18 62 67` ou `06 17 18 62 67`)
4. Match avec la table `users` (sur les 9 derniers chiffres)
5. Si match : génère une réponse via LLM avec le system persona d'ARIA
6. Envoie via deep link `https://wa.me/<phone>?text=<message>` (preserve les accents)
7. Log en DB (entrée `messages` + `last_seen` du user)
8. Dedup : diff des clés de notif entre poll précédent et actuel (évite de re-traiter la même notif)

### Démonstration end-to-end (sans gateway)

```bash
python tools/aria_reply_demo.py
```

Ouvre la conversation avec le user appairé, lit les messages, génère une réponse, l'envoie. Utile pour tester sans laisser le loop tourner.

---

## 🐛 Limites connues & bugs latents

- **`list_conversations` et `open_conversation` toujours sur OCR** : à migrer vers UI Automator (même pattern que `read_conversation`). OCR marche mais est plus lent (5-10s vs 3s) et moins précis.
- **`send_message` en mode tap-based perd les accents** : `adb input text` ne supporte pas l'UTF-8. Solution : utiliser le mode deep link (`phone=...`) qui passe par `urllib.parse.quote()`.
- **`press_back()` sur MIUI quitte la conversation** : piège connu, le bouton back Android ferme la nav avant le clavier. Éviter d'utiliser `press_back()` pour fermer le clavier.
- **Pas de gestion d'erreur réseau** : si le téléphone perd le Wi-Fi, le loop crash. À wrapper dans un retry.
- **Le LLM peut fabuler** : ARIA peut inventer des activités ("j'ai passé la matinée à lire des trucs sur les trous noirs") sans que ce soit vrai. Le system prompt doit explicitement demander de ne pas mentir.

---

## 🔒 Sécurité & éthique

- Ne jamais versionner `.env`, `aria.db`, les credentials
- ARIA ne doit pas se faire passer pour un humain de façon trompeuse sur les plateformes publiques
- Les comptes X/WhatsApp doivent idéalement être identifiés comme un compte IA
- Les logs locaux peuvent contenir des données sensibles — traiter en conséquence
- `redact_credentials()` masque les codes à 4-8 chiffres (codes de vérif, OTP) dans tout ce qui est loggé en DB. C'est un garde-fou essentiel vu qu'ARIA manipule des conversations où des credentials circulent (PayPal, etc.)

---

## 📜 Licence

MIT — projet personnel, fork bienvenu.

---

*ARIA est un projet expérimental. Elle existe parce qu'un téléphone qui dort dans un tiroir méritait mieux.*
