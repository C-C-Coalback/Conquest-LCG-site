import json
from django.http import JsonResponse
from play.consumers import create_bot_game, active_games, condition_games
import os
from django.views.decorators.csrf import csrf_exempt
from decks.consumers import deck_check_and_save
from asgiref.sync import async_to_sync


def api_index(request):
    return JsonResponse({
        "status": "ok",
        "endpoints": {
            "skills": "/api/skills/",
            "auth_token": "/api/auth-token/",
            "create_bot_room": "/api/create_bot_room/",
            "send_deck_text": "/api/send_deck_text/",
            "request_deck": "/api/request_deck/",
            "ai_lobby": "/api/ai_lobby/<hash>/",
            "ai_join": "/api/ai_join/<hash>/",
            "ai_game": "/api/ai_game/<game_id>/",
            "ai_action": "/api/ai_action/<game_id>/",
            "ai_decks": "/api/ai_decks/<bot_name>/"
        }
    })


def _parse_skill_frontmatter(content):
    """Parse YAML frontmatter from SKILL.md content."""
    metadata = {}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
            for line in frontmatter.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    metadata[key.strip()] = value.strip()
    return metadata


def _get_available_skills():
    """Scan skills directory for SKILL.md files."""
    skills = []
    skills_dir = os.path.join(os.getcwd(), "skills")
    if not os.path.exists(skills_dir):
        return skills
    
    for skill_id in os.listdir(skills_dir):
        skill_path = os.path.join(skills_dir, skill_id, "SKILL.md")
        if os.path.exists(skill_path):
            with open(skill_path, "r") as f:
                content = f.read()
            metadata = _parse_skill_frontmatter(content)
            skills.append({
                "id": skill_id,
                "name": metadata.get("name", skill_id),
                "description": metadata.get("description", ""),
                "url": f"/api/skills/{skill_id}/"
            })
    return skills


def skills_list(request):
    """List all available skills."""
    skills = _get_available_skills()
    return JsonResponse({"skills": skills})


def skill_detail(request, skill_id):
    """Return full SKILL.md content for a given skill."""
    skill_path = os.path.join(os.getcwd(), "skills", skill_id, "SKILL.md")
    if not os.path.exists(skill_path):
        return JsonResponse({"status": "error", "error": "Skill not found"}, status=404)
    
    with open(skill_path, "r") as f:
        content = f.read()
    
    metadata = _parse_skill_frontmatter(content)
    return JsonResponse({
        "id": skill_id,
        "name": metadata.get("name", skill_id),
        "description": metadata.get("description", ""),
        "content": content
    })

@csrf_exempt
def create_bot_room(request):
    print(request.method)
    if request.method == "POST":
        try:
            data = request.POST.dict()
            print(data)
            bot_name_1 = data["name1"]
            bot_name_2 = data["name2"]
            game_id = data["id"]
            private = data["private"]
            errata = "No Errata"
            sector = "Traxis Sector"
            print(private)
            if private == "False":
                private = False
            else:
                private = True
            print(type(private))
            game_id = create_bot_game(bot_name_1, bot_name_2, game_id, errata, sector, private=private)
            response = {
                'status': 'success',
                "id": game_id
            }
        except json.JSONDecodeError:
            response = {
                'status': 'error',
                'error': 'Incorrect JSON usage'
            }
        except:
            response = {
                'status': 'error',
                'error': "server error 500"
            }
    else:
        response = {
            'status': 'error',
            'error': 'Only POST requests allowed'
        }
    return JsonResponse(response)


@csrf_exempt
def receive_raw_deck_text(request):
    if request.method != "POST":
        response = {
            "status": "error",
            "error": "Not POST request"
        }
        return JsonResponse(response)
    data = request.POST.dict()
    try:
        bot_name = data["name"]
        deck = data["deck_text"]
        print(deck)
        result_of_saving = deck_check_and_save(bot_name, deck)
        response = {
            "status": result_of_saving["message"]
        }
    except KeyError as e:
        response = {
            "status": "error",
            "error": f"Missing required field: {str(e)}"
        }
    except Exception as e:
        response = {
            "status": "error",
            "error": "server error 500",
            "details": str(e)
        }
    return JsonResponse(response)


@csrf_exempt
def request_deck_text_given_name(request):
    if request.method != "POST":
        response = {
            "status": "error",
            "error": "Not POST request"
        }
        return JsonResponse(response)
    data = request.POST.dict()
    try:
        bot_name = data["name"]
        deck_name = data["deck_name"]
        target_deck_dir = os.getcwd() + "/decks/DeckStorage/" + bot_name + "/" + deck_name
        if not os.path.exists(target_deck_dir):
            response = {
                "status": "error",
                "error": "Deck does not exist"
            }
        else:
            with open(target_deck_dir, "r") as file:
                deck_text = file.read()
            response = {
                "status": "success",
                "deck_text": deck_text
            }
    except KeyError as e:
        response = {
            "status": "error",
            "error": f"Missing required field: {str(e)}"
        }
    except Exception as e:
        response = {
            "status": "error",
            "error": "server error 500",
            "details": str(e)
        }
    return JsonResponse(response)


def get_ai_lobby_by_hash(request, ai_hash):
    """
    Query a lobby by its AI join hash.
    Returns lobby details if found, error otherwise.
    """
    from play.consumers import active_lobbies
    
    if request.method != "GET":
        return JsonResponse({"status": "error", "error": "Only GET requests allowed"})
    
    # Search for lobby with matching AI hash
    for lobby in active_lobbies:
        if len(lobby) > 9 and lobby[9] == ai_hash:
            # Found the lobby
            response = {
                "status": "success",
                "lobby": {
                    "player_one": lobby[0],
                    "player_two": lobby[1],
                    "private": lobby[2],
                    "errata": lobby[3],
                    "sector": lobby[4],
                    "deck_one": lobby[5],
                    "deck_two": lobby[6],
                    "time_created": lobby[7],
                    "first_player": lobby[8],
                    "ai_hash": lobby[9]
                }
            }
            return JsonResponse(response)
    
    return JsonResponse({"status": "error", "error": "Lobby not found"}, status=404)


@csrf_exempt
def ai_join_lobby(request, ai_hash):
    """
    Bot joins a lobby by AI join hash.
    The bot becomes player_two in the lobby.
    """
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    from play.consumers import active_lobbies
    
    if request.method != "POST":
        return JsonResponse({"status": "error", "error": "Only POST requests allowed"})
    
    data = request.POST.dict()
    bot_name = data.get("bot_name", "Conqueror")
    bot_deck = data.get("deck_name", "")
    
    # Search for lobby with matching AI hash
    for i, lobby in enumerate(active_lobbies):
        if len(lobby) > 9 and lobby[9] == ai_hash:
            # Check if lobby is still open (player_two is empty)
            if lobby[1] != "":
                return JsonResponse({"status": "error", "error": "Lobby is already full"})
            
            # Bot joins the lobby
            active_lobbies[i][1] = bot_name
            active_lobbies[i][6] = bot_deck
            
            # Notify all WebSocket clients about the lobby update
            try:
                channel_layer = get_channel_layer()
                # Send updated lobby list to all clients
                for j, lobby_data in enumerate(active_lobbies):
                    ai_hash_val = lobby_data[9] if len(lobby_data) > 9 else ""
                    message = "Create lobby/" + lobby_data[0] + "/" + lobby_data[1] + "/" \
                              + lobby_data[2] + "/" + lobby_data[3] + "/" + lobby_data[4] + \
                              "/" + lobby_data[7] + "/" + lobby_data[8] + "/false" + "/" + ai_hash_val
                    async_to_sync(channel_layer.group_send)(
                        "lobby",
                        {"type": "chat.message", "message": message}
                    )
            except Exception as e:
                # Log error but don't fail the join
                print(f"Error notifying WebSocket clients: {e}")
            
            response = {
                "status": "success",
                "message": f"Bot {bot_name} joined lobby",
                "lobby": {
                    "player_one": active_lobbies[i][0],
                    "player_two": active_lobbies[i][1],
                    "private": active_lobbies[i][2],
                    "errata": active_lobbies[i][3],
                    "sector": active_lobbies[i][4],
                    "deck_one": active_lobbies[i][5],
                    "deck_two": active_lobbies[i][6],
                    "time_created": active_lobbies[i][7],
                    "first_player": active_lobbies[i][8],
                    "ai_hash": active_lobbies[i][9]
                }
            }
            return JsonResponse(response)
    
    return JsonResponse({"status": "error", "error": "Lobby not found"}, status=404)


def _find_active_game(game_id):
    for game in active_games:
        if game.game_id == game_id:
            return game
    return None


def _bot_side_for_game(game, bot_name):
    if game.name_1 == bot_name:
        return 1
    if game.name_2 == bot_name:
        return 2
    return None


def _parse_request_data(request):
    data = request.POST.dict()
    if not data and request.body:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return None
    return data


def _build_info_box(game):
    """Build a structured view of what the human info-box is showing."""
    raw = getattr(game, "last_info_box_string", "") or ""
    hint = getattr(game, "last_hint_string", "") or ""
    parts = [p for p in raw.split("/") if p != ""]
    # Format: GAME_INFO / INFO_BOX / <waiting_on> / Phase: X / Mode: Y / ...details...
    waiting_on = parts[2] if len(parts) > 2 else ""
    details = parts[3:] if len(parts) > 3 else []
    return {
        "raw": raw,
        "hint": hint,
        "waiting_on": waiting_on,
        "details": details,
        "text": " | ".join(details) if details else "",
    }


def _build_prompt(game, bot_name):
    """Build the current decision prompt for the bot, if any."""
    choices = list(game.choices_available) if game.choices_available else []
    waiting_on = game.name_player_making_choices or ""
    is_bots_turn_to_choose = bool(choices) and waiting_on == bot_name
    binary = False
    yes_index = None
    no_index = None
    if len(choices) == 2 and set(c.lower() for c in choices) == {"yes", "no"}:
        binary = True
        for i, c in enumerate(choices):
            if c.lower() == "yes":
                yes_index = i
            elif c.lower() == "no":
                no_index = i
    return {
        "active": bool(choices),
        "is_bots_turn": is_bots_turn_to_choose,
        "context": game.choice_context or "",
        "waiting_on": waiting_on,
        "choices": choices,
        "binary_yes_no": binary,
        "yes_index": yes_index,
        "no_index": no_index,
        "how_to_answer": (
            "POST /api/ai_action/<game_id>/ with {\"bot_name\": \"...\", \"answer\": \"Yes\"|\"No\"} "
            "or {\"action\": \"CHOICE/<index>\"}"
            if is_bots_turn_to_choose else
            "No answer expected from this bot right now."
        ),
    }


def _parse_deck_summary(deck_text):
    lines = [ln for ln in deck_text.splitlines() if ln.strip() and set(ln.strip()) != {"-"}]
    warlord = lines[1] if len(lines) > 1 else ""
    faction = lines[2] if len(lines) > 2 else ""
    return {"warlord": warlord, "faction": faction}


def list_ai_decks(request, bot_name):
    """List decks available to a bot under decks/DeckStorage/<bot_name>/."""
    if request.method != "GET":
        return JsonResponse({"status": "error", "error": "Only GET requests allowed"}, status=405)

    deck_dir = os.path.join(os.getcwd(), "decks", "DeckStorage", bot_name)
    if not os.path.isdir(deck_dir):
        return JsonResponse({"status": "error", "error": f"No deck storage for {bot_name}"}, status=404)

    decks = []
    for deck_name in sorted(os.listdir(deck_dir)):
        path = os.path.join(deck_dir, deck_name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r") as f:
                summary = _parse_deck_summary(f.read())
        except Exception:
            summary = {"warlord": "", "faction": ""}
        decks.append({
            "deck_name": deck_name,
            "warlord": summary["warlord"],
            "faction": summary["faction"],
        })

    return JsonResponse({"status": "success", "bot_name": bot_name, "decks": decks})


def _game_snapshot(game, bot_name):
    side = _bot_side_for_game(game, bot_name)
    if side is None:
        return None
    bot_player = game.p1 if side == 1 else game.p2
    opp_player = game.p2 if side == 1 else game.p1
    return {
        "status": "success",
        "game_id": game.game_id,
        "bot_name": bot_name,
        "bot_side": side,
        "phase": game.phase,
        "mode": game.mode,
        "info_box": _build_info_box(game),
        "prompt": _build_prompt(game, bot_name),
        "automated_data": getattr(game, "last_automated_data_string", "") or "",
        "bot": {
            "name": bot_player.name_player,
            "deck_loaded": bot_player.deck_loaded,
            "resources": bot_player.resources,
            "hand": list(bot_player.cards),
            "deck_count": len(bot_player.deck),
            "warlord": bot_player.headquarters[0].get_name() if bot_player.headquarters else "",
            "faction": getattr(bot_player, "warlord_faction", "") or "",
        },
        "opponent": {
            "name": opp_player.name_player,
            "deck_loaded": opp_player.deck_loaded,
            "resources": opp_player.resources,
            "hand_count": len(opp_player.cards),
            "deck_count": len(opp_player.deck),
            "warlord": opp_player.headquarters[0].get_name() if opp_player.headquarters else "",
            "faction": getattr(opp_player, "warlord_faction", "") or "",
        },
    }


def get_ai_game(request, game_id):
    """
    Return a bot-facing snapshot of an active game.

    Primary fields for decision-making:
      - info_box: what the human UI info-box is saying
      - prompt: current choice/question, including Yes/No mapping when binary
      - bot.hand: cards currently in the bot hand
    """
    if request.method != "GET":
        return JsonResponse({"status": "error", "error": "Only GET requests allowed"}, status=405)

    bot_name = request.GET.get("bot_name", "Conqueror")
    game = _find_active_game(game_id)
    if game is None:
        return JsonResponse({"status": "error", "error": "Game not found"}, status=404)

    snapshot = _game_snapshot(game, bot_name)
    if snapshot is None:
        return JsonResponse({"status": "error", "error": f"{bot_name} is not a player in this game"}, status=403)
    return JsonResponse(snapshot)


@csrf_exempt
def ai_game_action(request, game_id):
    """
    Submit a bot game action over REST.

    Preferred for binary prompts (most common):
      {"bot_name": "Conqueror", "answer": "Yes"} or {"answer": "No"}

    Deck loading (SETUP):
      {"bot_name": "Conqueror", "load_deck": "BLOOD FOR THE BLOOD GOD"}
      {"bot_name": "Conqueror", "load_random": true}

    Also accepted:
      {"bot_name": "Conqueror", "action": "CHOICE/1"}
      {"bot_name": "Conqueror", "action": "pass-P1"}
      {"bot_name": "Conqueror", "action": "HAND/1/0"}
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "error": "Only POST requests allowed"}, status=405)

    data = _parse_request_data(request)
    if data is None:
        return JsonResponse({"status": "error", "error": "Incorrect JSON usage"}, status=400)

    bot_name = data.get("bot_name", "Conqueror")
    answer = (data.get("answer") or data.get("choice") or "").strip()
    action = (data.get("action") or "").strip()
    load_deck = (data.get("load_deck") or data.get("deck_name") or "").strip()
    load_random = str(data.get("load_random", "")).lower() in ("1", "true", "yes")

    game = _find_active_game(game_id)
    if game is None:
        return JsonResponse({"status": "error", "error": "Game not found"}, status=404)

    side = _bot_side_for_game(game, bot_name)
    if side is None:
        return JsonResponse({"status": "error", "error": f"{bot_name} is not a player in this game"}, status=403)

    # Deck loading path (uses same loaddeckbot/loadrandombot command handlers).
    if load_deck or load_random:
        if load_random:
            cmd_parts = ["", "loadrandombot", bot_name]
        else:
            cmd_parts = ["", "loaddeckbot", bot_name, load_deck]
        try:
            condition_games.acquire()
            async_to_sync(game.resolve_chat_message)(bot_name, cmd_parts)
        except Exception as e:
            return JsonResponse({
                "status": "error",
                "error": "server error 500",
                "details": str(e)
            }, status=500)
        finally:
            try:
                condition_games.notify_all()
                condition_games.release()
            except Exception:
                pass

        snapshot = _game_snapshot(game, bot_name)
        loaded = snapshot["bot"]["deck_loaded"] if snapshot else False
        return JsonResponse({
            "status": "success" if loaded else "error",
            "message": (
                f"Deck loaded for {bot_name}" if loaded else
                f"Deck load failed for {bot_name} (check deck name / storage)"
            ),
            "submitted_action": "/".join(cmd_parts),
            "load_deck": load_deck or None,
            "load_random": load_random,
            "game": snapshot,
        }, status=200 if loaded else 400)

    # Resolve simple Yes/No answers against the current prompt.
    if answer and not action:
        choices = list(game.choices_available) if game.choices_available else []
        if not choices:
            return JsonResponse({"status": "error", "error": "No active choice prompt"}, status=409)
        if game.name_player_making_choices != bot_name:
            return JsonResponse({
                "status": "error",
                "error": f"Choice is waiting on {game.name_player_making_choices}, not {bot_name}",
                "prompt": _build_prompt(game, bot_name),
                "info_box": _build_info_box(game),
            }, status=409)

        answer_l = answer.lower()
        matched_index = None
        for i, c in enumerate(choices):
            if c.lower() == answer_l:
                matched_index = i
                break
        if matched_index is None:
            # Also allow 0/1 numeric answers
            if answer_l.isdigit() and int(answer_l) < len(choices):
                matched_index = int(answer_l)
        if matched_index is None:
            return JsonResponse({
                "status": "error",
                "error": f"Answer '{answer}' not in choices",
                "choices_available": choices,
                "prompt": _build_prompt(game, bot_name),
            }, status=400)
        action = f"CHOICE/{matched_index}"

    if not action:
        return JsonResponse({
            "status": "error",
            "error": "Provide answer (Yes/No), load_deck, load_random, or action",
            "prompt": _build_prompt(game, bot_name),
            "info_box": _build_info_box(game),
        }, status=400)

    action_parts = [part for part in action.split("/") if part != ""]
    if not action_parts:
        return JsonResponse({"status": "error", "error": "Empty action"}, status=400)

    try:
        condition_games.acquire()
        game.game_events_as_mono_string += bot_name + "|||" + "/".join(action_parts) + "\n"
        async_to_sync(game.update_game_event)(bot_name, action_parts)
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": "server error 500",
            "details": str(e)
        }, status=500)
    finally:
        try:
            condition_games.notify_all()
            condition_games.release()
        except Exception:
            pass

    snapshot = _game_snapshot(game, bot_name)
    return JsonResponse({
        "status": "success",
        "message": f"Action applied for {bot_name}",
        "submitted_action": "/".join(action_parts),
        "submitted_answer": answer or None,
        "game": snapshot,
    })
