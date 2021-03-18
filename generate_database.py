#!/usr/bin/env python


import json
import os
import imagehash
import urllib # For url decoding
from PIL import Image
import time
import hashlib

library_path = './library'
db_path = 'db.json'
scryfall_db_path = 'oracle-cards-20210315090415.json'
scryfall_db = {}
with open(scryfall_db_path, 'r') as scryfall_db_file:
    scryfall_db = json.load(scryfall_db_file)

db = {}

if os.path.isfile(db_path):
    with open(db_path, 'r') as db_file:
        db = json.load(db_file)
else:
    db = {'cards':{}, 'hash_functions':[]}

def pretty_time_delta(seconds):
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days > 0:
        return '%dd%dh%dm%ds' % (days, hours, minutes, seconds)
    elif hours > 0:
        return '%dh%dm%ds' % (hours, minutes, seconds)
    elif minutes > 0:
        return '%dm%ds' % (minutes, seconds)
    else:
        return '%ds' % (seconds,)

def splitall(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts

def remove_extensions(path: str):
    path = os.path.splitext(path)[0] # Pull off first extension
    if '.back' in path:
        path = os.path.splitext(path)[0] # Pull off .back
    return path

class HashFunction(object):
    # We use the name hs instead of a better one to avoid collisions with **kwargs
    def __init__(self, function, hs, *args, **kwargs):
        if function.__module__ == "__main__":
            self.name = f'{function.__name__}'
        else:
            self.name = f'{function.__module__}.{function.__name__}'
        self.function = function
        self.hash_size = hs
        self.function_args = args
        self.function_kwargs = kwargs
        id_hash_input = str(self.name) + str(self.function_args) + str(self.function_kwargs)
        id_hash_input = id_hash_input.encode('UTF-8')
        self.id = hashlib.md5(id_hash_input).hexdigest()

    def hash(self, img):
        return self.function(img, *self.function_args, **self.function_kwargs)

    def serialize(self):
        return {
            'name': self.name,
            'hash_size': self.hash_size,
            'args': self.function_args,
            'kwargs': self.function_kwargs,
            'id': self.id
        }



def create_hash_functions():
    hash_functions = []
    for func in [imagehash.phash, imagehash.average_hash, imagehash.whash, imagehash.dhash, imagehash.dhash_vertical]:
        hash_function = HashFunction(func, 8) # 8 is default for these hashes
        hash_functions.append(hash_function)

    h = HashFunction(imagehash.colorhash, 3) # 3 is default for colorhash
    hash_functions.append(h)

    h = HashFunction(imagehash.phash, 10, hash_size=10)
    hash_functions.append(h)
    return hash_functions

# Adds list of HashFunctions to json db
def add_hash_functions(hash_functions: list[HashFunction]):
    for hash_function in hash_functions:
        # Only add function if it isn't on there yet
        if len([hf for hf in db['hash_functions'] if hf['id'] == hash_function.id]) == 0:
            print(f'Adding hash function with id {hash_function.id}')
            db['hash_functions'].append(hash_function.serialize())
        else:
            print(f'Hash function with id {hash_function.id} already exists. Skipping.')


def get_details_from_path(card_path):
    path_segments = splitall(card_path)
    set_name = path_segments[0]
    set_name = urllib.parse.unquote_plus(set_name)

    card_name = path_segments[1]
    card_name = urllib.parse.unquote_plus(card_name) # URL decode file name
    card_name = remove_extensions(card_name) # Strip extension

    side_name = path_segments[-1]
    side_name = urllib.parse.unquote_plus(side_name) # URL decode file name
    side_name = remove_extensions(side_name) # Strip extension
    return set_name, card_name, side_name

def get_card_id(card_path):
    set_name, card_name, _ = get_details_from_path(card_path)
    for card_obj in scryfall_db:
        if card_obj['name'] == card_name and card_obj['set_name'] == set_name:
            return card_obj['id']
    print(f"Couldn't find id for card {card_name} ({set_name}) at path {card_path}.")

def add_new_card(card_path, id):
    set_name, card_name, _ = get_details_from_path(card_path)

    db['cards'][id] = {
        'name': card_name,
        'set_name': set_name,
        'sides': {}
    }

def add_new_side(card_path: str, side: str, id: str):
    _, _, side_name = get_details_from_path(card_path)
    db['cards'][id]['sides'][side] = {
        'name': side_name,
        'hashes': []
    }

def hash_already_exists_for_side(card_obj, hash_func, side):
    if card_obj:
        side = card_obj['sides'].get(side)
        if side:
            hashes = side['hashes']
            if any([hash_func.id == hash['id'] for hash in hashes]):
                return True

    return False

def add_hash(img, card_path, id, hash_func, side="front"):
    card_obj = db['cards'].get(id)
    if hash_already_exists_for_side(card_obj, hash_func, side):
        #print(f'Already have hash function {hash_func.name} with args {hash_func.function_args}, {hash_func.function_kwargs}. Skipping')
        return

    hash = {
        'id': hash_func.id,
        'hash': str(hash_func.hash(img))
    }


    if not card_obj:
        add_new_card(card_path, id)

    card_obj = db['cards'][id]
    if not card_obj['sides'].get(side):
        add_new_side(card_path, side, id)

    side = card_obj['sides'][side]
    side['hashes'].append(hash)


def generate_db(hash_functions: list[HashFunction]):
    start_time = time.time()
    total_images = 0
    images_processed = 0
    for root, dirs, files in os.walk(library_path):
        total_images += len(files)
    for set_name in os.listdir(library_path):
        now = time.time()
        delta_time = now - start_time
        fraction_progress = images_processed/total_images
        if fraction_progress != 0:
            est_total_time = delta_time * 1/fraction_progress
            est_time_remaining = est_total_time * (1-fraction_progress)
            print(f'Processed {images_processed}/{total_images}. {round(fraction_progress*100, 2)}% est. {pretty_time_delta(est_time_remaining)}')
        set_path = os.path.join(library_path, set_name)
        if os.path.isdir(set_path):
            for card_name in os.listdir(set_path):
                card_path = os.path.join(set_path, card_name)

                # Single sided card
                if os.path.isfile(card_path):
                    img = Image.open(card_path)
                    relpath = os.path.relpath(card_path, library_path)
                    id = get_card_id(relpath)
                    for hash_func in hash_functions:
                        add_hash(img, relpath, id, hash_func)
                    images_processed += 1
                # Double sided card
                elif os.path.isdir(card_path):
                    for face_name in os.listdir(card_path):
                        face_path = os.path.join(card_path, face_name)
                        img = Image.open(face_path)
                        relpath = os.path.relpath(face_path, library_path)
                        id = get_card_id(relpath)
                        side = "back" if ".back" in face_path else "front"
                        for hash_func in hash_functions:
                            add_hash(img, relpath, id, hash_func, side=side)
                        images_processed += 1

if __name__ == "__main__":
    start = time.time()
    hash_functions = create_hash_functions()
    add_hash_functions(hash_functions)
    generate_db(hash_functions)
    #print(json.dumps(db, indent=2))
    with open(db_path, 'w') as db_file:
        db_file.write(json.dumps(db))
    end = time.time()
    print(pretty_time_delta(end - start))
