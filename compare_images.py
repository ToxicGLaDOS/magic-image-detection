#!/usr/bin/env python

from PIL import Image
import os
import imagehash
import numpy
import json
from typing import Union
import hashlib


def is_image(filename):
    f = filename.lower()
    return f.endswith(".png") or f.endswith(".jpg") or \
        f.endswith(".jpeg") or f.endswith(".bmp") or \
        f.endswith(".gif") or '.jpg' in f or  f.endswith(".svg")

db_path = 'db.json'
userpaths = ['./library']
image_filenames = []

db = {}
with open(db_path, 'r') as db_file:
    db = json.load(db_file)

# Represents the sum of many HashDeltas between two cards
class MultiHashDelta(object):
    def __init__(self, sum_normalized_deltas: str, lhs_card_id: str, rhs_card_id: str):
        self.sum_normalized_deltas = sum_normalized_deltas
        self.lhs_card_id = lhs_card_id
        self.rhs_card_id = rhs_card_id

    def __add__(self, other):
        if isinstance(other, HashDelta):
            if self.lhs_card_id != other.lhs_card_id:
                raise ValueError(f"lhs cards don't match. MultiHash: {self.lhs_card_id} SingleHash: {other.lhs_card_id}")
            elif self.rhs_card_id != other.rhs_card_id:
                raise ValueError(f"rhs cards don't match. MultiHash: {self.rhs_card_id} SingleHash: {other.rhs_card_id}")
            else:
                return MultiHashDelta(self.sum_normalized_deltas + other.normalized_value, self.lhs_card_id, self.rhs_card_id)
        else:
            raise TypeError(f"Can't add MultiHashDelta to {type(other)}")

class HashResult(object):
    def __init__(self, hash_function, hash_value, card_id):
        self.hash_function = hash_function
        self.value = hash_value
        try:
            str(self.value)
        except ValueError as e:
            print(f'card_id: {card_id}, hash_id: {self.hash_function.id}')
            raise e
        self.card_id = card_id

    def __sub__(self, other):
        if isinstance(other, HashResult):
            if self.hash_function.id == other.hash_function.id:
                try:
                    delta = self.value - other.value
                    return HashDelta(self.hash_function, delta, self.card_id, other.card_id)
                except TypeError as e:
                    print(f'Wrong shape {str(self.value)} and {str(other.value)}')
                    raise e

            else:
                raise TypeError(f"Can't subtract HashResults with different hash_functions ({self.hash_function.id} - {other.hash_function.id})")
        else:
            raise TypeError(f"Can't subtract {type(other)} from HashResult")

    def from_hex(hash_function, hex, card_id):
        return HashResult(hash_function, imagehash.hex_to_hash(hex), card_id)

class HashFunction(object):
    def __init__(self, function, *args, **kwargs):
        if function.__module__ == "__main__":
            self.name = f'{function.__name__}'
        else:
            self.name = f'{function.__module__}.{function.__name__}'
        self.function = function
        self.function_args = args
        self.function_kwargs = kwargs
        id_hash_input = str(self.name) + str(self.function_args) + str(self.function_kwargs)
        id_hash_input = id_hash_input.encode('UTF-8')
        self.id = hashlib.md5(id_hash_input).hexdigest()

    def __eq__(self, other):
        if isinstance(other, HashFunction):
            if self.id == other.id:
                return True
            else:
                return False
        else:
            return False

    def __ne__(self, other):
        return not self == other

    def hash(self, img, card_id):
        return HashResult(self, self.function(img, *self.function_args, **self.function_kwargs), card_id)



class HashDelta(object):
    def __init__(self, hash_function: HashFunction, value: Union[float, int], lhs_card_id: str, rhs_card_id: str):
        self.hash_function = hash_function
        self.value = value
        self.lhs_card_id = lhs_card_id
        self.rhs_card_id = rhs_card_id
        self.normalized_value = None

    def __add__(self, other):
        if isinstance(other, HashDelta):
            if self.hash_function == other.hash_function:
                raise TypeError(f"Shouldn't add deltas with same hash_function {hash_function.id}")
            else:
                if self.normalized_value == None:
                    raise ValueError(f"Can't add unnormalized HashDelta (lhs)")
                elif other.normalized_value == None:
                    raise ValueError(f"Can't add unnormalized HashDelta (rhs)")
                else:
                    return MultiHashDelta(self.normalized_value + other.normalized_value, self.lhs_card_id, self.rhs_card_id)
        # Let MultiHashDelta handle it
        elif isinstance(other, MultiHashDelta):
            return other + self
        else:
            raise TypeError(f"Can't add HashDelta to value of type {type(other)}")

    def normalize_to(self, value: Union[float, int]):
        assert self.value <= value
        self.normalized_value = self.value / value # Puts it in range 0-1



# Get's HashFunction from hash dict data
def get_hash_function(hash: dict) -> HashFunction:
    if '.' in hash['name']:
        split = hash['name'].split('.')
        module = globals()[split[0]]
        function = getattr(module, split[1])
        args = hash['args']
        kwargs = hash['kwargs']
    else:
        raise Exception("Hash function with no module not supported yet")
    hash_function = HashFunction(function, *args, **kwargs)
    return hash_function

# Get's all the HashFunctions from the database
def get_hash_functions(json_db) -> list[HashFunction]:
    hash_functions = []
    for hash_dict in json_db['hash_functions']:
        hash_functions.append(get_hash_function(hash_dict))

    return hash_functions

# Get's the HashResults for the reference image
def get_reference_hashes(reference_image: Image, card_id: str, hash_functions: list[HashFunction]) -> list[HashResult]:

    hash_results = []

    for hash_function in hash_functions:
        result = hash_function.hash(reference_image, card_id)
        hash_results.append(result)

    return hash_results

# Get's hash result from list of hash objects in db that matches given hash.
# Card_id is given to pair with the HashResult for easier correlation later on
def get_hash_result_from_hash_list(hash_list: list[dict], hash_function: HashFunction, card_id: str) -> HashResult:
    for hash in hash_list:
        if hash['id'] == hash_function.id:
            hr = HashResult.from_hex(hash_function, hash['hash'], card_id)
            return hr
    raise Exception(f"No hash with id {id} found in list of hashes {hashes}")

def get_hash_result_from_list_by_id(hash_list: list[HashResult], id: str):
    for hash_result in hash_list:
        if hash_result.hash_function.id == id:
            return hash_result
    raise Exception(f"No HashResult in list with HashFunction having id {id}")

# Creates a list of HashResults for a specific HashFunction over the card_objs dict
def get_hash_results_from_db(hash_function: HashFunction, card_objs: dict) -> list[HashResult]:
    hash_results = []
    for card_id, card_obj in card_objs.items():
        card_name = card_obj['name']
        set_name = card_obj['set_name']
        sides = card_obj['sides']
        for side in sides.values():
            side_name = side['name']
            hashes = side['hashes']
            hash = get_hash_result_from_hash_list(hashes, hash_function, card_id)
            hash_results.append(hash)

    return hash_results

def get_normalized_hash_deltas(reference_hash_result: HashResult, hash_results: list[HashResult]) -> list[HashDelta]:
    deltas = [hash_result - reference_hash_result for hash_result in hash_results]
    max_value = max(delta.value for delta in deltas)
    for delta in deltas:
        delta.normalize_to(max_value)

    return deltas

def get_sum_lists(list_a: list, list_b: list):
    assert len(list_a) == len(list_b)
    return [list_a[i] + list_b[i] for i in range(len(list_a))]

def compare_hashes(reference_hashes: list[HashResult], hash_functions: list[HashFunction], json_db: dict):
    card_objs_dict = json_db['cards']
    multi_hash_deltas = []

    for hash_function in hash_functions:
        reference_hash = get_hash_result_from_list_by_id(reference_hashes, hash_function.id)
        hash_results = get_hash_results_from_db(hash_function, card_objs_dict)
        normalized_hash_deltas = get_normalized_hash_deltas(reference_hash, hash_results)
        # On first pass just add the normalized hash deltas to the list
        if len(multi_hash_deltas) == 0:
            multi_hash_deltas.extend(normalized_hash_deltas)
        else:
            multi_hash_deltas = get_sum_lists(multi_hash_deltas, normalized_hash_deltas)


if __name__ == "__main__":
    test_image = Image.open('heliods_pilgrim.jpg')
    test_image = test_image.rotate(-90, expand=True)
    test_image = test_image.resize((488, 680))

    hash_functions = get_hash_functions(db)
    reference_hashes = get_reference_hashes(test_image, "reference_card", hash_functions)
    compare_hashes(reference_hashes, hash_functions, db)
