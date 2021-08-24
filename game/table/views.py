from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from .models import (CardCollection, CardCollectionForm,
                     WhiteCard,
                     BlackCard,
                     Player, PlayerForm,
                     Game, GameForm)
from .forms import UploadFileForm, CreateGame
from json import loads
import uuid

import redis
from django.conf import settings
REDIS_HOST, REDIS_PORT = settings.CHANNEL_LAYERS["default"]["CONFIG"]["hosts"][0]
redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

def index(request):

    return redirect('table-lobby')

def manage(request):
    if request.method == 'POST':
        if request.POST['whichform'] == 'newcollection':
            c = CardCollectionForm(request.POST)
            new_collection = c.save()
            return redirect('table-manage-collection', pk=new_collection.id)

        elif request.POST['whichform'] == 'bulkupload':
            form = UploadFileForm(request.POST, request.FILES)
            if form.is_valid():
                f = request.FILES['file']
                l = loads(f.read())
                decks = l['packs']
                white = l['white']
                black = l['black']

                for deck in decks:

                    collection, _ = CardCollection.objects.get_or_create(title=deck['name'],
                                                                         official=deck['official'])
                    for card_index in deck['white']:
                        w = WhiteCard.objects.create(text=white[card_index])
                        w.collections.add(collection)
                        w.save()
                    for card_index in deck['black']:
                        b = BlackCard.objects.create(text=black[card_index]['text'], card_plays=black[card_index]['pick'])
                        b.collections.add(collection)
                        b.save()

        return redirect(manage)

    elif request.method == 'GET':
        collections = CardCollection.objects.all()
        uploadform = UploadFileForm()

        passin = {'CardCollectionForm': CardCollectionForm,
                  'collections': collections,
                  'uploadform': uploadform}

        return render(request, 'table/manage.html', passin)
    else:
        return HttpResponse("Method not supported")

def collectionedit(request, pk=None):

    collection = get_object_or_404(CardCollection, id=pk)
    collections = CardCollection.objects.all()

    passin = {'collection': collection,
              'other_collections': collections}

    return render(request, 'table/editcollection.html', passin)


def register(request):

    passin = {'playerform': PlayerForm()}

    if request.method == 'GET':
        return render(request, 'table/register.html', passin)
    elif request.method == 'POST':
        player = PlayerForm(request.POST).save()

        r = redirect(lobby)
        r.set_cookie('secret', player.secret, max_age=None, httponly=True)

        return r

    else:
        return HttpResponse("Method unsupported")


def endgame(request, gameid):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    game_obj = get_object_or_404(Game, id=gameid)
    game_obj.game_over = True
    game_obj.save()
    return redirect(lobby)


def lobby(request):

    uid = request.COOKIES.get('secret')
    if uid:
        try:
            player = Player.objects.get(secret=request.COOKIES.get('secret'))
        except Player.DoesNotExist:
            return redirect(register)
    else:
        return redirect(register)


    gameform = GameForm()
    if request.method == 'POST':
        gameform = GameForm(request.POST)
        if gameform.is_valid():
            g = Game.objects.create(name=gameform.cleaned_data['name'])


            return redirect('configure-game', g.id)

    passin = {'player': player,
              'games': Game.objects.filter(ready=True),
              'gameform': gameform}

    return HttpResponse(render(request, 'table/lobby.html', passin))

def game(request, pk):
    game_obj = get_object_or_404(Game, id=pk)

    if not game_obj.ready:
        return redirect(configure_game, pk)

    uid = request.COOKIES.get('secret')
    player = None
    if uid:
        player = Player.objects.get(secret=request.COOKIES.get('secret'))
    if not player:
        return redirect(register)


    # Cleanup player object and get a hand dealt if player is joining game for first time
    if player.id not in [int(i) for i in redis.lrange(f'game:{game_obj.id}:player', 0, -1)]:

        redis.rpush(f'game:{game_obj.id}:player', player.id)

        # Mark default ready status
        redis.set(f'game:{game_obj.id}:player:{player.id}:ready', 'no')

        # Set starting score to 0
        redis.set(f'game:{game_obj.id}:player:{player.id}:score', 0)



    passin = {'player': player,
              'game': game_obj}

    # If no card_czar then this must be the first player. Assign them as card czar
    if not redis.get(f'game:{game_obj.id}:card_czar'):
        redis.set(f'game:{game_obj.id}:card_czar', player.id)

    return render(request, 'table/game.html', passin)

def configure_game(request, pk):
    uid = request.COOKIES.get('secret')
    player = None
    if uid:
        player = Player.objects.get(secret=request.COOKIES.get('secret'))
    if not player:
        return redirect(register)
    game_obj = get_object_or_404(Game, id=pk)

    if game_obj.ready:
        return redirect(game, pk)

    if request.method == 'POST':

        postdecks = request.POST.get('decks')
        if type(postdecks) != str:
            raise Exception("INVALID POST")
        for deck_id in postdecks.split(","):
            try:
                deck = CardCollection.objects.get(id=deck_id)
            except CardCollection.DoesNotExist:
                continue
            w = deck.whitecard_set.all()
            b = deck.blackcard_set.all()
            if w:
                redis.sadd(f"game:{game_obj.id}:deck:white", *[str(i.id) for i in w])
            if b:
                redis.sadd(f"game:{game_obj.id}:deck:black", *[str(i.id) for i in b])

        game_obj.ready = True
        game_obj.save()

        # Assign initial active black card
        bcardid = redis.spop(f"game:{game_obj.id}:deck:black", 1)[0]
        redis.set(f"game:{game_obj.id}:activeblackcard", bcardid)

        return redirect('table-game', game_obj.id)
    passin = {
        'game': game_obj,
        'player': player,
        'all_decks': CardCollection.objects.all().order_by("title")
    }

    return render(request, 'table/configure_game.html', passin)