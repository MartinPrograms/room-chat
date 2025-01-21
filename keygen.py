# Keygen.py

import random
import string

def keygen():
    key = ''
    for i in range(64):
        key += random.choice(string.ascii_letters + string.digits)
    return key

print(keygen())