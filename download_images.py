#!/usr/bin/env python

import json
import os
import time
import shutil
import requests
import urllib


card_library = 'library'

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

def download_image(image_url, dest_path):
    response = requests.get(image_url, stream=True)

    if response.status_code == 200:
        # Set decode_content value to True, otherwise the downloaded image file's size will be zero.
        response.raw.decode_content = True

        # Open a local file with wb ( write binary ) permission.
        with open(dest_path, 'wb') as f:
            shutil.copyfileobj(response.raw, f)
    elif response.status_code == 429:
        print("Downloading too fast. Got 429 (Too many requests)")
    else:
        print("Error downloading file")


def load_json(json_file):
    json_obj = None
    with open(json_file, 'r') as json_file:
        json_obj = json.load(json_file)
    print(f'{len(json_obj)} card objects loaded')
    return json_obj

def download_face(name, set_name, image_url, download_dir):
    if not os.path.exists(download_dir):
        os.makedirs(download_dir) # Creates parents too

    download_path = os.path.join(download_dir, urllib.parse.quote_plus(name + '.jpg'))
    if os.path.exists(download_path):
        print(f'{name} ({set_name}) already exists at {download_path}.')
    else:
        print(f'Downloading {name} ({set_name}) from {image_url} to {download_path}.')
        download_image(image_url, download_path)
        time.sleep(0.055) # Sleep for 55 milliseconds. See rate limiting here: https://scryfall.com/docs/api


def download_images(json_obj):
    if not os.path.exists(card_library):
        os.mkdir(card_library)
    for entry in json_obj:
        card_set_name = entry['set_name']
        card_set_name_encoded = urllib.parse.quote_plus(card_set_name)
        # Double sided card
        if entry.get('image_uris', None) == None:
            card_faces = entry['card_faces']
            download_dir = os.path.join(card_library, card_set_name_encoded, urllib.parse.quote_plus(entry['name']))
            for index, face in enumerate(card_faces):
                card_name = face['name']
                # Append .back to card name if it has the same name as the front side
                if index > 0 and card_name == card_faces[0]['name']:
                    card_name += '.back'
                card_image_url = face['image_uris']['normal'] # Download the "normal" card size
                download_face(card_name, card_set_name, card_image_url, download_dir)
        # Single sided card
        else:
            card_name = entry['name']
            card_image_url = entry['image_uris']['normal'] # Download the "normal" card size
            download_dir = os.path.join(card_library, card_set_name_encoded)
            download_face(card_name, card_set_name, card_image_url, download_dir)

if __name__ == "__main__":
    start = time.time()
    json_obj = load_json('oracle-cards-20210315090415.json')
    download_images(json_obj)
    end = time.time()
    print(f'Completed download in {pretty_time_delta(end - start)}.')
