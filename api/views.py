import json
from django.http import JsonResponse
from play.consumers import create_bot_game
import os
from django.views.decorators.csrf import csrf_exempt
from decks.consumers import deck_check_and_save


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
            "ai_join": "/api/ai_join/<hash>/"
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
