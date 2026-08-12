from django.urls import path, include
from django.contrib.auth.models import User
from rest_framework import routers, serializers, viewsets
from rest_framework.authtoken.views import obtain_auth_token

from . import views

urlpatterns = [
    path("", views.api_index, name="api_index"),
    path("auth-token/", obtain_auth_token),
    path("skills/", views.skills_list, name="skills_list"),
    path("skills/<str:skill_id>/", views.skill_detail, name="skill_detail"),
    path("create_bot_room/", views.create_bot_room, name="create_bot_room"),
    path("send_deck_text/", views.receive_raw_deck_text, name="receive_raw_deck_text"),
    path("request_deck/", views.request_deck_text_given_name, name="request_deck_text_given_name"),
    path('ai_lobby/<str:ai_hash>/', views.get_ai_lobby_by_hash, name='get_ai_lobby_by_hash'),
    path('ai_join/<str:ai_hash>/', views.ai_join_lobby, name='ai_join_lobby'),
]
