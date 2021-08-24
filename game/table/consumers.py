from uuid import uuid4 as uuid
from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync
from .models import Player, Game, WhiteCard, BlackCard
import redis
from django.conf import settings
REDIS_HOST, REDIS_PORT = settings.CHANNEL_LAYERS["default"]["CONFIG"]["hosts"][0]
redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)


class GameConsumer(JsonWebsocketConsumer):

    def connect(self):

        if not self.scope["user"].is_authenticated:
            self.close()
            return

        self.player = Player.objects.get(secret=self.scope['cookies']['secret'])
        self.game   = Game.objects.get(id=self.scope['url_route']['kwargs']['pk'])
        self.room_group_name = f"game_{self.game.id}"

        # Auth for user token / name
        if not (self.player and self.game):
            self.close()
            return

        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        redis.set(f'game:{self.game.id}:player:{self.player.id}:channel', self.channel_name)

        self.accept()

        self.init_ui()

        if self.card_czar:
            self.card_czar = True  # Trigger UI to render card czar

        self.set_blackcard()

        # init list of users
        playerids = [int(i) for i in redis.lrange(f'game:{self.game.id}:player', 0, -1)]
        players = Player.objects.filter(id__in=playerids)
        for player in players:
            player_status = redis.get(f'game:{self.game.id}:player:{player.id}:ready').decode('utf-8')
            self.set_player_status(player.name, player_status)

        czar = Player.objects.get(id=int(redis.get(f'game:{self.game.id}:card_czar'))).name
        self.set_player_status(czar, 'czar')

    def disconnect(self, close_code):
        #TODO remove user from game cleanly

        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    ##################
    # misc functions #
    ##################

    def init_ui(self, *args):
        # Check for correct number of cards. If less than hand size then draw new cards and add them
        while redis.zlexcount(f'game:{self.game.id}:player:{self.player.id}:hand', '-', '+') < 10:
            # Draw a new card out
            card = redis.spop(f"game:{self.game.id}:deck:white")
            if not card:
                self._broadcast_channel('end_game', 'white')
                self._broadcast_channel('deck_count', '')
                return
            # add card to hand
            redis.zadd(f'game:{self.game.id}:player:{self.player.id}:hand', {card: 0})

        # Have the client render hand
        card_ids = redis.zrange(f'game:{self.game.id}:player:{self.player.id}:hand', 0, -1)
        white_cards = WhiteCard.objects.filter(id__in=card_ids)
        # Have client render whitecard hand
        for card in white_cards:
            self.add_whitecard(card)

        # Trigger hand to unhide if not card czar
        if not self.card_czar:
            self._send_action('show_playerhand', '')
        # Will trigger @properties setter to render status on UIs
        self.player_ready = self.player_ready
        self._broadcast_channel('deck_count', '')

    ###########################################################
    # Functions to call client side API for rendering changes #
    ###########################################################
    def add_whitecard(self, card):
        self._send_action('add_whitecard', {'add_id': card.id,
                                            'add_text': card.text})

    def replace_whitecard(self, old_card, new_card):
        self._send_action('replace_whitecard', {'add_id': new_card.id,
                                                'add_text': new_card.text,
                                                'replace_id': old_card.id})

    def send_console(self, message: str, level='info'):
        self._send_action('console', {level: message})

    def disable_choose_card(self, *args):
        # *args allows this to be called via async channels which always provides an argument
        if not self.card_czar:
            self._send_action('disable_submit', '')

    def enable_choose_card(self, *args):
        # *args allows this to be called via async channels which always provides an argument
        if not self.card_czar:
            self._send_action('enable_submit', '')

    def set_blackcard(self, *args):
        # *args allows this to be called via async channels which always provides an argument
        cardid = redis.get(f"game:{self.game.id}:activeblackcard")
        text = BlackCard.objects.get(id=int(cardid)).text
        self._send_action('set_blackcard', text)

    def set_player_status(self, name, status):
        # If called via channels status is a dict and will be unpacked.
        # If called directly status is a string and is
        # Possible status Values, ready, notready, czar, czar_choosing

        # alternate storage name for redis, covert to standard
        if status == 'no':
            status = 'notready'
        elif status == 'yes':
            status = 'ready'

        player_id = id_by_name_game(name, self.game.id)
        # Get player's current score
        score = redis.get(f'game:{self.game.id}:player:{player_id}:score')
        if not score:
            score = 0
        else:
            score = int(score)

        self._send_action('player_status', {'name': name,
                                            'status': status,
                                            'score': score,
                                            'player_id': player_id})

    def winner_posted(self, card_text, winning_playername, czar_playername):
        self._send_action('show_playerhand', '')
        self._send_action('winner_posted', {
                                'card_text': card_text,
                                'winning_playername': winning_playername,
                                'czar_playername': czar_playername
                          })

    def end_game(self, *args):
        self.game.game_over = True
        self.game.save()
        self._send_action("end_game", '')

    def deck_count(self, *args):
        white = redis.scard(f'game:{self.game.id}:deck:white')
        black = redis.scard(f'game:{self.game.id}:deck:black')
        self._send_action('card_count', {'white': white, 'black': black})


    ################################################
    # Properties to make redis queries transparent #
    ################################################
    @property
    def card_czar(self):
        if int(redis.get(f'game:{self.game.id}:card_czar')) == self.player.id:
            return True
        return False

    @card_czar.setter
    def card_czar(self, value: bool):
        if value:
            redis.set(f'game:{self.game.id}:card_czar', self.player.id)
            self._send_action('start_cardczar', '')
            self._broadcast_channel('channel_set_player_status', {'name': self.player.name, 'status': 'czar'})

        else:
            raise Exception("Cannot un-assign card czar. Another player must assign this True to take ownership")

    @property
    def player_ready(self):
        if redis.get(f'game:{self.game.id}:player:{self.player.id}:ready') == b'yes':
            return True
        return False

    @player_ready.setter
    def player_ready(self, value):
        if self.card_czar:
            return
        if value:
            redis.set(f'game:{self.game.id}:player:{self.player.id}:ready', 'yes')
            self.disable_choose_card()
            status = 'ready'
        else:
            redis.set(f'game:{self.game.id}:player:{self.player.id}:ready', 'no')
            self.enable_choose_card()
            status = 'notready'

        self._broadcast_channel('channel_set_player_status', {'name': self.player.name, 'status': status})


    def action_choose_winner(self, *args):
        if not self.card_czar:
            return

        # Make sure all players are marked as ready
        self._broadcast_channel('channel_set_player_ready', 'yes')
        self._broadcast_channel('channel_set_player_status', {'name': self.player.name, 'status': 'czar_choosing'})

        # Make a dict of all cards played this round key:id_of_card value:text_on_card
        cards = {}
        # TODO replace redis.keys call with a dedicated index set for lookups
        for roundid in [i.decode('utf-8').split(':')[4] for i in
                        redis.keys(f'game:{self.game.id}:round:playedcards:*')]:
            cards[roundid] = []
            for cardid in [int(i) for i in redis.lrange(f'game:{self.game.id}:round:playedcards:{roundid}', 0, -1)]:
                cards[roundid].append(WhiteCard.objects.get(id=cardid).text)

        self._send_action('choosing_cardczar', cards)

        # Have all other players render the cards the cardczar is looking at
        self._broadcast_channel('channel_show_candidate_cards', list(cards.values()))



    ###################################################################
    ### Receive Functions for ingesting incoming websocket messages ###
    ###################################################################
    def receive_json(self, message):
        action = message['action']
        if 'data' in message:
            data = message['data']
        else:
            data = None

        if action == 'play_whitecard':
            # Rename data to something more descriptive
            cardid = int(data)

            if self.player_ready:
                self.send_console("You are done chief. Enough cards played", level='error')
                return
            if cardid not in [int(i) for i in redis.zrange(f'game:{self.game.id}:player:{self.player.id}:hand', 0, -1)]:
                self.send_console("This card is not in your hand", level='error')
                return

            # Remove card from their hand
            redis.zrem(f'game:{self.game.id}:player:{self.player.id}:hand', cardid)

            # Get round ID or create a new one. This is to track who submits what white card(s)
            roundid = redis.get(f'game:{self.game.id}:round:playerid:{self.player.id}')
            if roundid:
                roundid = roundid.decode('utf-8')
            else:
                roundid = uuid().hex
                redis.set(f'game:{self.game.id}:round:playerid:{self.player.id}', roundid)
                redis.set(f'game:{self.game.id}:round:roundid:{roundid}', self.player.id)

            # Append the card to the right of the list of played cards.
            #  Use roundid to hide player when rendering for czar
            redis.rpush(f'game:{self.game.id}:round:playedcards:{roundid}', cardid)

            # Check to see if enough cards have been played for specific Black Card
            bcardid = redis.get(f"game:{self.game.id}:activeblackcard")
            card_plays = BlackCard.objects.get(id=int(bcardid)).card_plays
            if redis.llen(f'game:{self.game.id}:round:playedcards:{roundid}') >= card_plays:
                # Enough cards have been played. re-draw new cards, and end turn
                for cardid in [int(i) for i in redis.lrange(f'game:{self.game.id}:round:playedcards:{roundid}', 0, -1)]:

                    # Draw a new card out
                    card = redis.spop(f"game:{self.game.id}:deck:white")
                    if not card:
                        self._broadcast_channel('end_game', 'white')
                        self._broadcast_channel('deck_count', '')
                        return
                    # add card to hand
                    redis.zadd(f'game:{self.game.id}:player:{self.player.id}:hand', {card: 0})

                    # have UI replace card in hand
                    new_card = WhiteCard.objects.get(id=int(card))
                    old_card = WhiteCard.objects.get(id=cardid)
                    self.replace_whitecard(old_card, new_card)

                # Mark player as ready for this round. Make them ineligible to play another card
                self.player_ready = True

                players = [int(i) for i in redis.lrange(f'game:{self.game.id}:player', 0, -1)]
                for player in players:
                    if int(redis.get(f'game:{self.game.id}:card_czar')) != player:  # Dont check readyness for card czar
                        if redis.get(f'game:{self.game.id}:player:{player}:ready').decode('utf-8') == "no":
                            break
                else:
                    # For loop will only enter here if break was not encountered. thus all players are ready
                    #  Trigger all players to run action_choose_winner. all will NOP except czar
                    self._broadcast_channel('action_choose_winner')
            self._broadcast_channel('deck_count', '')

        elif action == 'choosewinner':
            self.action_choose_winner()

        elif action == 'skipround':
            czar_id = int(redis.get(f'game:{self.game.id}:card_czar'))
            czar_name = Player.objects.get(id=czar_id).name
            skip_info = {'skipper': self.player.name, 'skipped': czar_name}
            self._broadcast_channel('channel_set_player_status', {'name': czar_name, 'status': 'notready'})
            self._broadcast_channel('channel_skip_czar', skip_info)
            self.new_round()

        elif action == 'choosewinningcard':
            roundid = data

            if not self.card_czar:
                self.send_console('you are not the card czar, cant choose winners, you loser', level='error')
                return
            winner_id = redis.get(f'game:{self.game.id}:round:roundid:{roundid}')
            if not winner_id:
                self.send_console('What exactly are you trying to do. cant pick an ID that is invalid', level='error')
                return
            else:
                winner_id = int(winner_id)

            card_text = []
            for cardid in redis.lrange(f'game:{self.game.id}:round:playedcards:{roundid}', 0, -1):
                card_text.append(WhiteCard.objects.get(id=int(cardid)).text)


            # Lookup winning player's name
            #  Save this information to render at the end.
            #  Must pop up toast after UIs have stablized, but this information must be gathered now
            winner_info = {
                'card_text': card_text,
                'winning_playername': Player.objects.get(id=winner_id).name,
                'czar_playername': self.player.name
            }
            self._broadcast_channel('channel_winner_posted', winner_info)

            # Increment the winner's score and update their status
            redis.incr(f'game:{self.game.id}:player:{winner_id}:score')
            self.winner_posted(**winner_info)
            self.new_round()





        else:
            self.send_console('unknown action', level='error')

    def _send_action(self, action, data):
        self.send_json(
            {
                'action': action,
                'data': data
            }
        )

    ##################################################
    ### Methods for async channels group messaging ###
    ##################################################
    def _broadcast_channel(self, method_name, message=None):
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': method_name,
                'message': message
            }
        )

    def channel_set_player_status(self, chdict):
        # The channels method, this simply unpacks the dict and calls the more friendly version
        #  allows us to keep the set_player_status method friendly for direct calls outside of channels
        name = chdict['message']['name']
        status = chdict['message']['status']
        self.set_player_status(name, status)

    def channel_set_player_ready(self, chdict):
        if chdict['message'] == 'yes':
            self.player_ready = True
        elif chdict['message'] == 'no':
            self.player_ready = False

    def channel_winner_posted(self, chdict):
        msg = chdict['message']
        self.winner_posted(msg['card_text'], msg['winning_playername'], msg['czar_playername'])

    def channel_set_czar(self, chdict):
        if chdict['message'] == self.player.id:
            self.card_czar = True


    def channel_show_candidate_cards(self, chdict):
        if self.card_czar:
            return
        cards = chdict['message']
        self._send_action('show_candidate_cards', cards)

    def channel_skip_czar(self, chdict):
        # chdict['message'] keys should be skipper and skipped
        self._send_action('skip_notification', chdict['message'])



    ###################

    def new_round(self):
        # Cleanup Round
        #  TODO there is an incredibly small chance bad things could happen here.
        #   Should use LUA script to make atomic
        for k in redis.scan_iter(f'game:{self.game.id}:round:*'):
            redis.delete(k)


        # Pass Card Czar onto the next player
        # Push current czar to end of the line
        redis_playerlist = f'game:{self.game.id}:player'
        redis.rpush(redis_playerlist, redis.lpop(redis_playerlist))
        # Get new left end player from list
        new_czar = int(redis.lindex(redis_playerlist, 0))

        # Have all players mark themselves not ready
        self._broadcast_channel('channel_set_player_ready', 'no')

        # There is a way to direct message via channels, cant remember, dirty hack for now.
        #  Just send the message to everyone inside redis, and ignore if you are not the player id
        self._broadcast_channel('channel_set_czar', new_czar)



        # Pick a new blackcard and trigger all clients to re-render it
        bcardid = redis.spop(f"game:{self.game.id}:deck:black")
        if not bcardid:
            self._broadcast_channel('end_game', 'black')
            self._broadcast_channel('deck_count', '')
            return
        redis.set(f"game:{self.game.id}:activeblackcard", bcardid)
        self._broadcast_channel('set_blackcard')
        self._broadcast_channel('deck_count', '')


def id_by_name_game(name, gameid):
    player_ids = [int(i) for i in redis.lrange(f'game:{gameid}:player', 0, -1)]
    player = Player.objects.filter(id__in=player_ids).filter(name=name)
    if player:
        return player[0].id