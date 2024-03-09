import sys
import os
import argparse

import dtmf
from goertzel import Goertzel

import soundfile as sf

verbosef = False


def debug(n, *args, **kwargs):
    if verbosef >= n:
        print(*args, **kwargs)


def resolvesymbol(gr, threshold):
    freqs = []
    # check what detectors found their target frequency
    for g in gr:
        p = g.power()
        debug(1, g.f, f'{p:2.2f}', end='')
        if p > threshold:
            freqs.append(g.f)
            debug(1, ' *')
        else:
            debug(1, '')
    if len(freqs) == 2:
        # exactly two frequencies detected, find corresponding symbol
        for e in dtmf.ALL_SYMBOLS:
            if freqs[0] in e[1] and freqs[1] in e[1]:
                # symbol found
                (fl, fh) = e[1]
                print(
                    f'SYMBOL:"{e[0]}"', f'({fl}Hz, {fh}Hz)')
                return (True, e[0])
    else:
        debug(1, "NO SYMBOL")
        return (False, 0)


def compare_numbers(decoded_numbers):
    # Expected numbers in the audio data
    expected_numbers = [
        '0696675356',
        '4646415180',
        '2336731416',
        '3608338160',
        '4400826146',
        '6253689638',
        '8482138178',
        '5073643399'
    ]
    # Compare expected to the actually decoded numbers
    for n in range(0, len(expected_numbers)):
        if expected_numbers[n] != decoded_numbers[n]:
            print("ERROR expected number %s does not match decoded %s" %
                  (expected_numbers[n], decoded_numbers[n]))


def main():

    parser = argparse.ArgumentParser(description='DTMF detector')
    parser.add_argument('-v', '--verbose', default=0,
                        action='count', help='verbose mode')
    # parser.add_argument('--test', action='store_true', help="Self-test")
    # parser.add_argument('--demo', metavar='mode', default=1,
    #                    type=int, help='Demo mode [1|2|3|4]')
    # parser.add_argument('-p', '--port', metavar='port', help='Serial port')
    # parser.add_argument('-c', '--cmd', nargs='+', metavar='CMD', required=True, help='Command list: LEFT, RIGHT or RESET')
    parser.add_argument('audiofile')
    args = parser.parse_args()

    global verbosef
    verbosef = args.verbose

    audiopath = args.audiofile
    if not os.path.exists(audiopath):
        print(f'File not found: {audiopath}')
        return
    (data, fs) = sf.read(audiopath, dtype='float32')
    print(f'{audiopath} {len(data)/fs:.2f}s samplerate: {fs}Hz')

    # Number of useable samples depends on the sample rate. Higher sample rates give better accuracy.
    N = int(0.9 * dtmf.TONE_TIME * fs)

    # Required goertzel detectors for each DTFM frequency
    gr = [
        Goertzel(dtmf.FREQ_LOW1, N, fs),
        Goertzel(dtmf.FREQ_LOW2, N, fs),
        Goertzel(dtmf.FREQ_LOW3, N, fs),
        Goertzel(dtmf.FREQ_LOW4, N, fs),
        Goertzel(dtmf.FREQ_HIGH1, N, fs),
        Goertzel(dtmf.FREQ_HIGH2, N, fs),
        Goertzel(dtmf.FREQ_HIGH3, N, fs),
        Goertzel(dtmf.FREQ_HIGH4, N, fs)
    ]

    envelope = 0
    signal = 0  # active signal start timestamp
    number = []  # dialed number
    lastts = -dtmf.PAUSE_TIME  # last number found
    # threshold = 5  # frequency detect treshold power
    envelopesample = 0

    decoded_numbers = []

    def addnumber():
        dial = ''.join(number)
        print("DIAL", dial)
        decoded_numbers.append(dial)
        number.clear()

    def signal_off():
        nonlocal lastts
        duration = t - signal
        debug(2, f'{t:.2f}s', "SIGNAL OFF", f'{int(duration*1000)}ms')
        if duration > dtmf.TONE_TIME * 0.8:  # ignore if too short signal
            debug(1, f'ENVELOPE {envelopesample:2.1f}')
            (detect, symbol) = resolvesymbol(gr, envelopesample * 0.5)
            if detect:
                number.append(symbol)
            lastts = t

    def signal_on():
        nonlocal signal
        nonlocal envelopesample
        interval = t - lastts  # only consider signal if enough time has passed since the last one
        if interval > dtmf.PAUSE_TIME * 0.8:
            debug(2, f'{t:.2f}s', "SIGNAL ON",
                  f'{int(interval*1000)}ms')
            signal = t
            envelopesample = 0
            for g in gr:  # reset goertzel detectors
                g.reset()

    # Process data samples
    for (n, s) in enumerate(data):
        t = n/fs  # timestamp
        # rough envelope detector
        envelope = 0.95*envelope + abs(s)
        if envelope >= 1.0:  # signal amplitude is strong enough
            if not signal:
                signal_on()
        else:  # no signal detected
            if signal:
                signal_off()
                signal = 0
            continue
        if signal:
            for g in gr:  # update detectors with the sample
                if not g.ready():  # no need for new samples if already enough
                    if g.update(s):  # enough samples, store envelope status for thresholding
                        envelopesample = envelope

        # if enough time has passed since last detected digit assume the whole dialed number has been decoded
        if t - lastts > 0.3 and len(number):
            addnumber()

    if signal:
        signal_off()

    if len(number):
        addnumber()

    # self test
    # compare_numbers(decoded_numbers)


if __name__ == "__main__":
    main()
