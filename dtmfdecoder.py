import sys
import argparse
import queue

import sounddevice as sd
import soundfile as sf

from goertzel import Goertzel, dtmf


class DTFMDecoder():

    def __init__(self, verbose, samplerate, envelope_threshold=2.0):

        self.verbose = verbose

        # Number of useable samples depends on the sample rate. Higher sample rates give better accuracy.
        N = int(0.9 * dtmf.TONE_TIME * samplerate)

        # Goertzel detector for each DTMF frequency
        self.goertzels = [
            Goertzel(dtmf.FREQ_LOW1, N, samplerate),
            Goertzel(dtmf.FREQ_LOW2, N, samplerate),
            Goertzel(dtmf.FREQ_LOW3, N, samplerate),
            Goertzel(dtmf.FREQ_LOW4, N, samplerate),
            Goertzel(dtmf.FREQ_HIGH1, N, samplerate),
            Goertzel(dtmf.FREQ_HIGH2, N, samplerate),
            Goertzel(dtmf.FREQ_HIGH3, N, samplerate),
            Goertzel(dtmf.FREQ_HIGH4, N, samplerate)
        ]
        self.samplerate = samplerate
        self.envelope_threshold = envelope_threshold

    def resolvesymbol(self, threshold):
        freqs = []
        # check what detectors found their target frequency and match the found frequency pair
        # to DTMF symbol.
        for g in self.goertzels:
            p = g.power()
            if p > threshold:
                freqs.append(g.f)
            if self.verbose:
                print(f'{g.f} {p:2.2f} {" *" if p > threshold else ""}')
        if len(freqs) == 2:
            # exactly two frequencies detected, find corresponding symbol
            for e in dtmf.SYMBOLS:
                if freqs[0] in e[1] and freqs[1] in e[1]:
                    # symbol found
                    (symbol, (fl, fh)) = e
                    print(
                        f'SYMBOL:"{symbol}"', f'({fl}Hz, {fh}Hz)')
                    return symbol
        else:
            print("NO SYMBOL FOUND")
            return ''

    def start(self):
        self.reset()

    def reset(self):
        self.envelope = 0
        self.signalts = 0
        self.lastts = -dtmf.PAUSE_TIME
        self.envelopesample = 0
        self.ts = 0
        for g in self.goertzels:  # reset goertzel detectors
            g.reset()

    def process(self, data, symbolcb):  # process received audio blocks
        for s in data:
            sample = s[0]
            self.ts += 1/self.samplerate  # timestamp
            t = self.ts
            # rough envelope detector.
            self.envelope = 0.95*self.envelope + abs(sample)
            if self.envelope >= self.envelope_threshold:  # signal amplitude is strong enough
                if not self.signalts:
                    # only consider signal if enough time has passed since the last one
                    interval = t - self.lastts
                    if interval > dtmf.PAUSE_TIME * 0.8:  # signal acquired
                        if self.verbose > 1:
                            print(f'{t:.2f}s', "SIGNAL ON",
                                  f'{int(interval*1000)}ms')
                        self.signalts = t
                        self.envelopesample = 0
                        for g in self.goertzels:  # reset goertzel detectors
                            g.reset()
            else:  # no signal detected
                if self.signalts:  # signal lost
                    duration = t - self.signalts
                    if self.verbose > 1:
                        print(f'{t:.2f}s', "SIGNAL OFF",
                              f'{int(duration*1000)}ms')
                    if duration > dtmf.TONE_TIME * 0.8:  # ignore if too short signal
                        print(f'ENVELOPE {self.envelopesample:2.1f}')
                        symbol = self.resolvesymbol(
                            self.envelopesample / 3)
                        if symbol:
                            symbolcb(symbol)
                        # self.lastts = t
                        self.lastts = self.ts = 0
                    self.signalts = 0
                continue
            if self.signalts:
                for g in self.goertzels:  # update detectors with the sample
                    if not g.ready():  # no need for new samples if already enough
                        # enough samples, store envelope status for thresholding
                        if g.update(sample):
                            self.envelopesample = self.envelope


DEBUG_RECORD = 'dtmf_demo_rec.wav'


def open_recordfile(filename, samplerate):
    subtype = 'PCM_16'
    if filename:
        print("Recording to", filename)
        # open soundfile and start recording until user hangs up
        return sf.SoundFile(filename, mode='w', samplerate=samplerate, channels=1, subtype=subtype)
    return None


def main():
    parser = argparse.ArgumentParser(description='DTMF signal decoder')
    parser.add_argument('-v', '--verbose', default=0,
                        action='count', help='verbose mode')
    parser.add_argument('-r', '--record', nargs='?',
                        const=DEBUG_RECORD, metavar='FILE', help='Record audio')
    args = parser.parse_args()

    port = None
    verbose_level = args.verbose

    # print audio devices
    device = sd.query_devices(kind='input')
    if device:
        print(f'AUDIO INPUT: {device["name"]}')
    else:
        print("ERROR: No input audio device found")
        exit(1)

    SAMPLERATE = 14400
    print(f'Sample rate {SAMPLERATE}Hz')
    recordfile = open_recordfile(args.record, SAMPLERATE)

    q = queue.Queue()

    # Called (from a separate thread) for each audio block.
    def callback(indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        q.put(indata.copy())

    decoder = DTFMDecoder(verbose_level, SAMPLERATE)

    # For some reason Python sounddevice recorded audio can be -6dB compared to e.g. Audacity 100% recording level.
    # I suspect it's caused by forcing a mono recording from a stereo device. See https://github.com/PortAudio/portaudio/issues/397
    # Stereo device produces mono signal by summing and halving to avoid clipping.  M = (L + R)/2
    istream = sd.InputStream(
        samplerate=SAMPLERATE, blocksize=0, channels=1, callback=callback)
    istream.start()

    def onkey(symbol):
        print(f'KEY {symbol}')

    print("Decoder started")
    decoder.start()

    while True:
        try:
            data = q.get(True)
            if recordfile:
                recordfile.write(data)
            decoder.process(data, onkey)
        except queue.Empty:
            pass
        except KeyboardInterrupt:
            print("Exiting...")
            break

    istream.stop()
    istream.close()
    if recordfile:
        recordfile.close()


if __name__ == '__main__':
    main()
