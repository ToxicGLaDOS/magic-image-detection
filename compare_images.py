#!/usr/bin/env python

from PIL import Image
import os
import imagehash
import numpy

def is_image(filename):
    f = filename.lower()
    return f.endswith(".png") or f.endswith(".jpg") or \
        f.endswith(".jpeg") or f.endswith(".bmp") or \
        f.endswith(".gif") or '.jpg' in f or  f.endswith(".svg")

userpaths = ['./library']
image_filenames = []

for userpath in userpaths:
    image_filenames += [os.path.join(userpath, path) for path in os.listdir(userpath) if is_image(path)]
images = {}

test_image = Image.open('heliods_pilgrim.jpg')
test_image = test_image.rotate(-90, expand=True)
test_image = test_image.resize((488, 680))
test_image.save('test_image.jpg')

#def phash(img):
#    sum_of_diffs = 0
#    values = range(8, 13)
#    for i in values:
#        sum_of_diffs += imagehash.phash(img, hash_size=i) - imagehash.phash(test_image, hash_size=i)
#    return sum_of_diffs/len(values)
#
#for img in sorted(image_filenames):
#        try:
#            diff = phash(Image.open(img))
#        except Exception as e:
#            print('Problem:', e, 'with', img)
#            continue
#        images[img] = images.get(img, []) + [diff]
#
#
#print(sorted(images.items(), key=lambda x: x[1]))

hashfuncs = [imagehash.phash, imagehash.average_hash, imagehash.whash, imagehash.colorhash, imagehash.dhash, imagehash.dhash_vertical]
#hashfuncs = [lambda img: imagehash.phash(img, hash_size=256)] # hash_size: 4 - 12 
#hashfuncs = [imagehash.dhash] # Good
#hashfuncs = [imagehash.dhash_vertical] # Good
#hashfuncs = [imagehash.phash] # Good
#hashfuncs = [imagehash.crop_resistant_hash] # Good
#hashfuncs = [imagehash.colorhash] # Good
#hashfuncs = [imagehash.average_hash] # Good
#hashfuncs = [imagehash.whash] # Good
#hashfuncs = [lambda img: imagehash.whash(img, mode='db4')] # Bad

for hashfunc in hashfuncs:
    for img in sorted(image_filenames):
        try:
            hash = hashfunc(Image.open(img))
        except Exception as e:
            print('Problem:', e, 'with', img)
            continue
        images[img] = images.get(img, []) + [hash]

test_image_hashes = []
for hashfunc in hashfuncs:
    test_image_hashes.append(hashfunc(test_image))


diffs = []
for image, hashes in images.items():
    diff = 0
    for x in range(len(hashfuncs)):
        if './library/thb-20-heliod-s-pilgrim.jpg' == image:
            print(str(hashes[x] - test_image_hashes[x]) + image)

        diff += hashes[x] - test_image_hashes[x]

    diffs.append((diff, image))

diffs.sort()


print(diffs)



