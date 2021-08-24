from django.contrib import admin

# Register your models here.

from .models import Game, Player, WhiteCard, BlackCard, CardCollection

for m in Game, Player, WhiteCard, BlackCard, CardCollection:
    admin.site.register(m)
