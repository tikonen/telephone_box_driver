import re
import math


def load_model_config(model):
    config = {}
    if model:
        print(f'Loading model configration {model}')
        with open(model, 'rt') as file:
            # matches: key:val
            kvpre = re.compile(
                r'^\s*(\w+)\s*:\s*([ -~]+)')
            # matches: # comment
            commentre = re.compile(r'^\s*#.*$')
            for line in file.readlines():
                line = line.strip()
                # skip empty lines and comments
                if line and not commentre.match(line):
                    m = kvpre.match(line)
                    if not m:
                        raise Exception(f'Invalid configuration {line}')
                    config[m[1]] = m[2]

    return config

# Increase audio volume


def adjust_volume(soundfile, db):
    (data, samplerate) = soundfile
    data *= math.pow(10, db/20)  # multiply amplitude
