from django.db import models
from django.forms import ModelForm, TextInput
from uuid import uuid1


class Setup(models.Model):

    key = models.CharField(max_length=64, primary_key=True)
    value = models.CharField(max_length=256)


class Game(models.Model):

    name = models.CharField(max_length=64)
    ready = models.BooleanField(default=False)
    game_over = models.BooleanField(default=False)


class GameForm(ModelForm):
    class Meta:
        model = Game
        fields = ['name']


class Player(models.Model):

    name = models.CharField(max_length=64)
    secret = models.CharField(max_length=64, default=uuid1)


class PlayerForm(ModelForm):
    class Meta:
        model = Player
        labels = {'name': ''}
        fields = ['name']
        widgets = {
            'name': TextInput(attrs={
                'id': "login",
                'class': "fadeIn second",
                'autofocus': "",
                'placeholder': "What shall we call you?"
            })
        }


class WhiteCard(models.Model):

    uuid = models.BinaryField(max_length=16, db_index=True)
    text = models.CharField(max_length=256)
    collections = models.ManyToManyField('CardCollection')


class BlackCard(models.Model):

    uuid = models.BinaryField(max_length=16, db_index=True)
    text = models.CharField(max_length=1024)
    collections = models.ManyToManyField('CardCollection')
    card_plays = models.IntegerField()


class CardCollection(models.Model):

    title = models.CharField(max_length=128, null=True)
    official = models.BooleanField(default=False)


class CardCollectionForm(ModelForm):
    class Meta:
        model = CardCollection
        fields = ['title',]

