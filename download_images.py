#!/usr/bin/env python

import json
import os
import time
import shutil
import requests



card_library = 'library'

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

def download_images(json_obj):
    for entry in json_obj[0:10]:
        card_name = entry['name']
        card_image_url = entry['image_uris']['normal'] # Download the "normal" card size
        card_set_name = entry['set_name']
        download_dir = os.path.join(card_library, card_set_name)
        if not os.path.exists(download_dir):
            os.mkdir(download_dir)

        download_path = os.path.join(download_dir, card_name + '.jpg')
        if os.path.exists(download_path):
            print(f'{card_name} ({card_set_name}) already exists at {download_path}.')
        else:
            print(f'Downloading {card_name} ({card_set_name}) from {card_image_url} to {download_path}.')
            download_image(card_image_url, download_path)
            time.sleep(0.055) # Sleep for 55 milliseconds. See rate limiting here: https://scryfall.com/docs/api

if __name__ == "__main__":
    json_obj = load_json('oracle-cards-20210315090415.json')
    download_images(json_obj)
