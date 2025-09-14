"""
beepcompress.py

Compresses raw export data from beep.sh for efficient storage and playback.

Usage:
    $ BEEP_EXPORT_RAW=1 ./beeps-master/sandstorm.sh | python beepcompress.py -p sandstorm_

Data Format:
-------------
The output consists of a header and compressed data:

Header:
    - 1 byte: Reserved
    - 1 byte: Number of unique keys (distinct values)
    - 2 bytes each: Value for each key (excluding zero, which is implicit)

Compressed Data:
    - Bit-packed key indices, where each key index is encoded using ceil(log2(number of keys)) bits.
    - The final byte is padded with zeros if necessary.

Example (3-bit keys, up to 7 possible values):
    Byte sequence: 0x64, 0x78
    Bit stream:    011 001 000 111 100 000 ...
    Decoded keys:  [3, 1, 0, 7, 4, 0, ...]

Notes:
    - The header maps key indices to their actual values.
    - Zero key represents value 0.
    - If compression is not efficient, the script outputs uncompressed data instead.

"""

#!python

import argparse
import sys
import re
from math import log2, ceil

parser = argparse.ArgumentParser(description='Beep compressor')
parser.add_argument('-v', '--verbose', default=0,
                    action='count', help='verbose mode')
parser.add_argument('-p', '--prefix', metavar='prefix',
                    default='', help='Variable prefix')
parser.add_argument('input', nargs='?', type=argparse.FileType('r'),
                    default=sys.stdin, help="Input file")
args = parser.parse_args()

tones = []
durations = []

linere = re.compile(r'([0-9]+) ([0-9]+)')

for line in args.input:
    line = line.strip()
    if line:
        m = linere.match(line)
        if not m:
            raise ValueError(f"Unknown line: \"{line}\"")
        tone = int(m[1])
        duration = int(m[2])
        if duration > 1:
            tones.append(tone)
            durations.append(duration)
            if duration < 20:
                print(
                    f"WARNING: short note {tone}Hz {duration}ms", file=sys.stderr)


def compress(data):
    # get key size
    dataset = set(data)
    dataset.add(0)  # always has 0
    numvals = len(dataset)
    keybits = ceil(log2(numvals))
    keymask = (1 << keybits) - 1

    # build value to key map
    keymap = {}
    key = 0
    for value in sorted(dataset):
        keymap[value] = key
        key += 1

    # compress data
    compressed = []
    out = 0
    avail = 0
    for value in data:
        out <<= keybits
        out |= keymap[value]
        avail += keybits
        if avail >= 8:
            # output a byte of compressed data
            outb = (out >> (avail - 8)) & 0xFF
            compressed.append(outb)
            avail -= 8

    padding = 0
    if avail > 0:  # last byte
        while 8 - avail >= keybits:
            # TODO: how to deal when there are more extra bits unused than the keysize. Then decode will output too many bytes.
            # For now just add filler keys
            out <<= keybits
            out |= keymap[0]
            # out |= keymask
            avail += keybits
            padding += 1
        outb = (out << (8 - avail)) & 0xFF
        compressed.append(outb)

    valuemap = {}
    for value in keymap.keys():
        valuemap[keymap[value]] = value

    return (compressed, valuemap, numvals, padding)


def decompress(data, valuemap, numvals):
    keybits = ceil(log2(numvals))
    keymask = (1 << keybits) - 1

    decompressed = []
    enc = 0
    avail = 0

    for b in data:
        enc |= b
        avail += 8
        while avail >= keybits:
            key = (enc >> (avail - keybits)) & keymask
            # if key != keymask:
            value = valuemap[key]
            decompressed.append(value)
            avail -= keybits
        enc <<= 8

    return decompressed


def export_data_arrays(data, type):
    # Export compressed data declaration arrays
    (encdata, valuemap, numvals, padding) = compress(data)
    # print(data, valuemap, numvals, padding)
    # print(decompress(data, valuemap, numvals))
    hdr = [numvals | padding << 13]
    for k in sorted(valuemap.keys())[1:]:
        hdr.append(valuemap[k])
    ratio = (2 * len(hdr) + 2 + len(encdata))/(2*len(data))

    if ratio > 1:
        newratio = (1 + 2 + (2*len(data)))/(2*len(data))
        print(
            f"// Uncompressed data. ratio {100*(1-newratio):0.1f}% (compression would be {100*(1-ratio):0.1f}%)")
        # build data packet
        packet = []
        packet.append(0xFF) # 255 as number of unique keys indicates uncompressed data
        encdatalen = len(data) * 2
        for v in data:
            packet.append(v & 0xFF)
            packet.append((v >> 8) & 0xFF)
        print(
            f"const uint8_t {args.prefix}{type}[] PROGMEM = {{{','.join(['0x{:02x}'.format(v) for v in packet])}}};")
    else:
        print(f"// Compression ratio {100*(1-ratio):0.1f}%")
        keybits = ceil(log2(numvals))
        print(f"// {numvals} unique keys. Key size {keybits} bits")

        # build data packet
        packet = []
        for v in hdr:
            packet.append(v & 0xFF)
            packet.append((v >> 8) & 0xFF)
        encdatalen = len(encdata)
        packet.append(encdatalen & 0xFF)
        packet.append((encdatalen >> 8) & 0xFF)
        packet += encdata

        print(
            f"const uint8_t {args.prefix}{type}[] PROGMEM = {{{','.join(['0x{:02x}'.format(v) for v in packet])}}};")
        print(f"#define {args.prefix}{type}HdrSize {len(hdr)*2}")
        print(f"#define {args.prefix}{type}EncSize {len(encdata)}")

    print(f"#define {args.prefix}{type}Size {len(packet)}")

    # print(
    #    f"const uint16_t {args.prefix}{type}DataHdr[] PROGMEM = {{{','.join([hex(v) for v in hdr])}}};")
    # print(f"#define {args.prefix}{type}DataHdrSize {len(hdr)*2}")
    # print(
    #    f"const uint8_t {args.prefix}{type}Data[] PROGMEM = {{{','.join([hex(v) for v in encdata])}}};")
    # print(f"#define {args.prefix}{type}DataSize {len(encdata)}")


# Export header file
print("#pragma once")
# print("// clang-format off")
export_data_arrays(tones, "toneNotes")
export_data_arrays(durations, "toneDurations")
