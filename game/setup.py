import urllib.request
from json import loads
from uuid import uuid5, NAMESPACE_OID
from table.models import Setup, WhiteCard, BlackCard, CardCollection


def populate_db():

    if not Setup.objects.filter(key='carddb').exists():
        url = 'https://raw.githubusercontent.com/crhallberg/json-against-humanity/latest/cah-all-compact.json'
        response = urllib.request.urlopen(url)
        rawdb = loads(response.read().decode('utf-8'))
        whitedeck = rawdb['white']
        blackdeck = rawdb['black']

        for pack in rawdb['packs']:
            print(f"Adding pack: {pack['name']}")
            db_collection = CardCollection.objects.create(
                title=pack['name'],
                official=pack['official']
            )
            whitecard_ids = pack['white']
            blackcard_ids = pack['black']

            for whitecard_id in whitecard_ids:
                db_whitecard = WhiteCard.objects.get_or_create(
                    uuid=uuid5(NAMESPACE_OID, whitedeck[whitecard_id]).bytes,
                    text=whitedeck[whitecard_id]
                )[0]
                db_whitecard.collections.add(db_collection)
                db_whitecard.save()

            for blackcard_id in blackcard_ids:
                blackcard = blackdeck[blackcard_id]
                db_blackcard = BlackCard.objects.get_or_create(
                    uuid=uuid5(NAMESPACE_OID, blackcard['text']).bytes,
                    text=blackcard['text'],
                    card_plays=blackcard['pick']
                )[0]
                db_blackcard.collections.add(db_collection)
                db_blackcard.save()

            db_collection.save()

        Setup.objects.create(key='carddb', value='url').save()
