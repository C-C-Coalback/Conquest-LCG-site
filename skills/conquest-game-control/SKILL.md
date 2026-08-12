---
name: conquest-game-control
description: Operate the local Conquest LCG app through its lobby websocket. Use this skill whenever the user asks to sign in, choose deck/faction, join or create a lobby, or start a live game at localhost:8000.
---

# Conquest Game Control (localhost)
Use this skill to reliably control a live game without rediscovering endpoints.

## Goal
- Join lobby/game as a real user account with a selected deck.
- Emit debug logs for decisions and actions.

## Official game rules digest (for agent play decisions)
Use this as the gameplay baseline when selecting legal actions.

- Official rule PDF's are here:
  * Full rules URL: https://images-cdn.fantasyflightgames.com/ffg_content/warhammer-40k-conquest/support/Learn-to-Play-web.pdf
  * Rules reference URL: https://images-cdn.fantasyflightgames.com/ffg_content/warhammer-40k-conquest/support/Rules-Reference-web.pdf

### Authoritative precedence
- If rules conflict: **card text > Rules Reference Guide (RRG) > Learn to Play**.
- Treat `cannot` as absolute.

### Win/loss conditions
- Win immediately if you claim **3 planets that share a common type icon**.
- Win immediately if the opponent’s **bloodied warlord is defeated**.
- Lose if your deck is empty when you must draw (engine/state should be treated as authoritative for this condition).

### First turn of the game
- On your very first turn of any game, you will be asked if you want to mulligan (redraw) your hand.
  * Look over your cards and make an estimated guess if you belive them to be adventagious towards your strategy to win.
    * Choosing **Yes** will give you a new hand
    * Choosing **No** will keep your current hand.
    
### Round structure (in order)
1. **Deploy phase**
2. **Command phase**
3. **Combat phase**
4. **Headquarters phase**

### Deploy phase essentials
- Players alternate deployment turns:
  - deploy one card, or
  - initiate one action, or
  - pass.
- After a player passes, that player takes no more deployment turns this phase.
- Phase ends when both players have passed.

### Command phase essentials
- Both players secretly set command dials, reveal simultaneously, then commit:
  - warlord + all HQ units move to the chosen planet number.
  - warlord arrives in current state; other committed HQ units arrive exhausted.
- Resolve command struggles from first planet downward:
  - if only one player has a ready warlord there, that player wins automatically;
  - otherwise compare command icons on ready units;
  - tie: neither player wins.
- Command winner may take both/either/none of that planet’s card/resource bonus.

### Combat phase essentials
- Battle at first planet, then check for additional battles as required by game state.
- Battle initiative:
  - if exactly one warlord is present at battle start, that side has initiative;
  - otherwise initiative token holder has initiative.
- Battle sequence:
  1) Ranged skirmish (ranged combat turns),
  2) regular combat rounds until battle ends.
- Attack sequence:
  1) declare ready attacker and exhaust it,
  2) declare defender,
  3) deal damage equal to attacker ATK.
- Damage handling:
  1) assign damage,
  2) optional shields (max 1 shield card per damaged unit),
  3) take remaining damage.
- Destruction/defeat:
  - army/token units at damage >= HP are destroyed,
  - hale warlord at damage >= HP becomes bloodied (damage cleared),
  - bloodied warlord defeated => controller loses.
- Retreat:
  - warlord may exhaust instead of attacking to retreat to HQ,
  - at end of combat round, each player may retreat any number of units to HQ exhausted.
- Winning a battle:
  - winner may trigger that planet’s Battle ability,
  - if won at first planet: winner claims that planet to victory display.

### Headquarters phase essentials
- Move first-planet token to next planet.
- Reveal next facedown planet (if any).
- Each player draws 2 cards.
- Each player gains 4 resources.
- Ready all cards.
- Pass initiative token.

### Timing windows and triggers
- **Action** abilities can be initiated only in action windows.
- **Interrupts** resolve before the triggering condition resolves.
- **Reactions** resolve after the triggering condition resolves.
- For both interrupts and reactions, initiative player gets first opportunity, then players alternate until both pass.

### Source documents
- `Learn-to-Play-web.pdf` (official Learn to Play)
- `Rules-Reference-web.pdf` (official Rules Reference Guide)

## Bundled helper script
- Autoplay helper: `skills/conquest-game-control/scripts/play_turn.py`
- Use it when the user wants immediate turn execution without re-implementing loop logic.
- Typical usage:
  - `python skills/conquest-game-control/scripts/play_turn.py --player <username>`
  - `python skills/conquest-game-control/scripts/play_turn.py --player <username> --game-id <game_id>`
- Useful flags:
  - `--run-seconds` to keep watching for your turn.
  - `--max-actions` to cap how many actions script may apply.
  - `--no-debug-commands` to skip debug command injection.

## Preconditions
- Server is reachable at `http://localhost:8000`.
- Account already exists.
- **Deck storage is pre-populated by server admin** under `decks/DeckStorage/<username>/`.
  - The bot/LLM cannot upload decks at runtime; decks must exist on the server beforehand.
  - To check available decks, use `GET /api/request_deck/` with `{"name": "<username>", "deck_name": ""}` to list decks, or browse `decks/DeckStorage/<username>/` directly.

## Lobby control over websocket
1. Create an authenticated HTTP session:
   - `GET /accounts/login/`
   - Parse `csrfmiddlewaretoken`.
   - `POST /accounts/login/` with `username`, `password`, CSRF token.
   - Confirm authenticated session (e.g. homepage contains “Logged in as <username>”).
2. Open websocket:
   - URL: `ws://localhost:8000/ws/play/`
   - Include session cookies in `Cookie` header.
3. Read initial messages:
   - Lobby rows arrive as `Create lobby/<host>/<guest>/...`.
   - Open lobby means `<guest>` is empty.
4. Choose deck and join:
   - Send `{"message":"Select Deck/<deck_name>"}`.
   - Send `{"message":"Join lobby/<host>/<deck_name>"}`.
5. Confirm join:
   - Success signal: `Create lobby/<host>/<your_username>/...`.

## REST API endpoints

### Discovery
- `GET /api/` - List all available endpoints
- `GET /api/skills/` - List available skills
- `GET /api/skills/<skill_id>/` - Get full skill documentation

### Authentication
- `POST /api/auth-token/` - Get authentication token
  - Request: `{"username": "...", "password": "..."}`
  - Response: `{"token": "..."}`

### Game management
- `POST /api/create_bot_room/` - Create a bot game room
  - Request: `{"name1": "...", "name2": "...", "id": "...", "private": "True|False"}`
  - Response: `{"status": "success", "id": "..."}`

### Deck management
- `POST /api/send_deck_text/` - Upload deck text
  - Request: `{"name": "...", "deck_text": "..."}`
  - Response: `{"status": "..."}`
- `POST /api/request_deck/` - Request deck text
  - Request: `{"name": "...", "deck_name": "..."}`
  - Response: `{"status": "success", "deck_text": "..."}`
- `GET /api/ai_decks/<bot_name>/` - List decks available to a bot with warlord/faction summary
  - Response: `{"status": "success", "bot_name": "...", "decks": [{"deck_name": "...", "warlord": "...", "faction": "..."}, ...]}`

### AI lobby management
- `GET /api/ai_lobby/<hash>/` - Query a lobby by AI join hash
  - Response: `{"status": "success", "lobby": {...}}` or `{"status": "error", "error": "Lobby not found"}`
- `POST /api/ai_join/<hash>/` - Bot joins a lobby by AI join hash
  - Request: `{"bot_name": "...", "deck_name": "..."}`
  - Response: `{"status": "success", "message": "...", "lobby": {...}}`

### AI in-game management (REST-only bot flow)
- `GET /api/ai_game/<game_id>/?bot_name=Conqueror` - Full game snapshot for the bot
  - Returns: `phase`, `mode`, `info_box` (what the human info-box shows), `prompt` (current choice with Yes/No mapping), `bot` (hand, deck_loaded, warlord, faction, resources), `opponent` (warlord, faction, deck_loaded, hand_count, deck_count)
- `POST /api/ai_action/<game_id>/` - Submit a bot action
  - Body fields (JSON):
    - `bot_name` (default `Conqueror`)
    - `answer`: `"Yes"` or `"No"` for binary prompts (preferred)
    - `action`: raw slash-path like `"CHOICE/1"`, `"pass-P1"`, `"HAND/1/0"`
    - `load_deck`: deck filename to load (SETUP only)
    - `load_random`: `true` to load a random deck (SETUP only)
  - Response: `{"status": "success", "message": "...", "submitted_action": "...", "game": {...}}`

## Post-join game startup checklist (REST-only)
**Do these in order as soon as the bot is in a live game. All steps use REST only — no WebSocket required.**

### Step 1: Read opponent faction
```http
GET /api/ai_game/<game_id>/?bot_name=Conqueror
```
- Read `opponent.warlord` and `opponent.faction`.
- Use this to pick a counter-deck.

### Step 2: List available decks and select one
```http
GET /api/ai_decks/Conqueror/
```
- Returns each deck with `deck_name`, `warlord`, `faction`.
- Pick a deck that counters the opponent's faction.

### Step 3: Load your deck
```http
POST /api/ai_action/<game_id>/
Body: {"bot_name": "Conqueror", "load_deck": "<deck_name>"}
```
- Or use `{"load_random": true}` for a random deck.
- Deck file must exist at `decks/DeckStorage/Conqueror/<deck_name>` (exact filename, including spaces).
- On success, response includes `game.bot.deck_loaded: true` and `game.bot.hand`.

### Step 4: Scan hand and answer mulligan
```http
GET /api/ai_game/<game_id>/?bot_name=Conqueror
```
- Read `bot.hand` (list of card names).
- Read `prompt`:
  - `prompt.active` — whether a choice is pending
  - `prompt.is_bots_turn` — whether the bot is the one being asked
  - `prompt.context` — e.g. `"Mulligan Opening Hand?"`
  - `prompt.binary_yes_no` — `true` when choices are exactly `["Yes", "No"]`
  - `prompt.yes_index` / `prompt.no_index` — which index maps to Yes/No

Answer via REST:
```http
POST /api/ai_action/<game_id>/
Body: {"bot_name": "Conqueror", "answer": "No"}
```
- Use `"Yes"` to mulligan (redraw), `"No"` to keep the hand.
- For non-binary prompts, use `{"action": "CHOICE/<index>"}` where index matches the choice position.

**Default strategy**: prefer `"No"` unless the hand is clearly unplayable.

**Mulligan order**: player 1 is asked first, then player 2. After both answer, the game proceeds to DEPLOY phase (or Necron enslaved-faction choice if applicable).

## WebSocket fallback (legacy)
For bots that need real-time event streaming, the WebSocket interface is still available:
- URL: `ws://localhost:8000/ws/play/<game_id>/`
- Deck load (must use double slash): `{"message": "CHAT_MESSAGE//loaddeckbot/<bot_username>/<deck_name>"}`
- Mulligan: `{"message": "BUTTON PRESSED/CHOICE/0"}` (Yes) or `CHOICE/1` (No)
- Single-slash `CHAT_MESSAGE/loaddeckbot/...` is treated as chat and will NOT load a deck.

## Game notes (mechanics)
- Planet reward values in engine data are stored as `(cards, resources)` order (not `(resources, cards)`), so a planet entry like `(0, 2)` means 0 cards and 2 resources.
- Command winner calculation in this engine uses command totals; warlords are represented with effectively auto-win command strength (`999`) unless opposed by another warlord.
- Helvetis has two separate effects at different times: command reward (`0 cards, 2 resources`) during command struggle resolution, and a separate forced activity coin-flip/indirect-damage effect when activities resolve in combat setup.

## General strategy notes
- Prefer proactive board/economy development over early passes when legal non-pass deploys exist.
- Keep resources and hand quality in mind across phases, not just the current legal action list.
- Opening hand decisions should prioritize a functional curve (early playable cards + economy/tempo plan) over narrow high-roll lines.

## Deck strategy notes
### Aunshi Assassin FFG
- Keep opening hands that already contain multiple early deploy options and command presence.
- Early `Ksi'm'yen Orbital City` deployment is a strong tempo line when legal and affordable.
- Cheap Tau units (`Ethereal Envoy`, `Bork'an Recruits`, `Vior'la Marksman`) are reliable early-game deploy pieces for command and board setup.
- In mirror-style openings, early command spread (for example, `Bork'an Recruits` to a non-first planet) can pressure economy while avoiding overcommitting to first-planet fights.
- Follow-up mirror line: after establishing off-first command pressure, deploying `Vior'la Marksman` to first planet helps contest first battle tempo without collapsing the wider command spread.
- With ~2 resources remaining in deploy, `Ethereal Envoy` to an uncontested mid planet is a strong efficiency line for incremental command advantage.
- With only ~1 resource left late in deploy, a final cheap unit to an uncontested trailing planet is often better than passing, because it widens command coverage going into command phase.
- In first-planet mirror combat, when forced to allocate indirect damage across your own units, splitting damage to preserve a live ranged attacker can outperform soaking everything on one body.
- In shield windows, preserving `Vior'la Marksman` for ranged pressure by spending lower-impact shield cards can be better than spending premium combat events.

### Debug logging
Before or during turns, send:
- `debug-info`
- `debug-reactions`
- `debug-interrupts`

And log per step:
- phase
- active player
- chosen action
- applied action

## Failure handling
- If login fails: report concise reason (bad creds, csrf parse failure, no session).
- If no open lobby: report currently visible lobbies and wait.
