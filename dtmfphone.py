import sys

from telephonebox import State, Command
from basicphone import BasicPhone

import sounddevice as sd
import soundfile as sf
import queue

from goertzel import Goertzel, dtmf

SAMPLERATE = 14400
VERBOSE = 1
# Number of useable samples depends on the sample rate. Higher sample rates give better accuracy.
N = int(0.9 * dtmf.TONE_TIME * SAMPLERATE)

# Goertzel detector for each DTMF frequency
goertzels = [
    Goertzel(dtmf.FREQ_LOW1, N, SAMPLERATE),
    Goertzel(dtmf.FREQ_LOW2, N, SAMPLERATE),
    Goertzel(dtmf.FREQ_LOW3, N, SAMPLERATE),
    Goertzel(dtmf.FREQ_LOW4, N, SAMPLERATE),
    Goertzel(dtmf.FREQ_HIGH1, N, SAMPLERATE),
    Goertzel(dtmf.FREQ_HIGH2, N, SAMPLERATE),
    Goertzel(dtmf.FREQ_HIGH3, N, SAMPLERATE)
]

# DEBUG_RECORD='dtmf_demo_rec.wav'
DEBUG_RECORD = None


def open_recordfile():
    subtype = 'PCM_16'
    filename = DEBUG_RECORD
    if filename:
        print("Recording to", filename)
        # open soundfile and start recording until user hangs up
        return sf.SoundFile(filename, mode='w', samplerate=SAMPLERATE, channels=1, subtype=subtype)
    return None


class DTMFPhone(BasicPhone):

    def __init__(self, port, verbose):
        super().__init__(port, verbose)
        global VERBOSE
        VERBOSE = verbose
        # Configure dial mode to none
        self.driver.command(Command.CONF, {'DM': 0})

    def key(self, symbol):
        print(f'KEY {symbol}')

    @staticmethod
    def resolvesymbol(threshold):
        freqs = []
        # check what detectors found their target frequency
        for g in goertzels:
            p = g.power()
            if p > threshold:
                freqs.append(g.f)
            if VERBOSE:
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

    # Phone is off-hook
    def wait(self):
        print("*** WAIT (OFFHOOK)")
        sd.play(self.dial_tone[0], self.dial_tone[1], loop=True)

        # Setup audio input and start monitoring dialed numbers
        q = queue.Queue()

        def callback(indata, frames, time, status):
            """Called (from a separate thread) for each audio block."""
            if status:
                print(status, file=sys.stderr)
            q.put(indata.copy())

        ENVELOPE_THRESHOLD = 1.0
        # For some reason Python sounddevice recorded audio is -6dB compared to e.g. Audacity 100% recording level.
        # I suspect it's caused by forcing a mono recording from a stereo device. See https://github.com/PortAudio/portaudio/issues/397
        # Stereo device produces mono signal by summing and halving to avoid clipping.  M = (L + R)/2

        # Increase gain if needed
        GAIN_DB = 0
        GAIN = 10**(GAIN_DB/20)  # gain as an amplitude scale factor

        def process(data):  # process received audio blocks
            for s in data:
                sample = s[0] * GAIN
                process.ts += 1/SAMPLERATE  # timestamp
                t = process.ts
                # rough envelope detector.
                process.envelope = 0.95*process.envelope + abs(sample)
                if process.envelope >= ENVELOPE_THRESHOLD:  # signal amplitude is strong enough
                    if not process.signalts:
                        # only consider signal if enough time has passed since the last one
                        interval = t - process.lastts
                        if interval > dtmf.PAUSE_TIME * 0.8:  # signal acquired
                            sd.stop()
                            if VERBOSE > 1:
                                print(f'{t:.2f}s', "SIGNAL ON",
                                      f'{int(interval*1000)}ms')
                            process.signalts = t
                            process.envelopesample = 0
                            for g in goertzels:  # reset goertzel detectors
                                g.reset()
                else:  # no signal detected
                    if process.signalts:  # signal lost
                        duration = t - process.signalts
                        if VERBOSE > 1:
                            print(f'{t:.2f}s', "SIGNAL OFF",
                                  f'{int(duration*1000)}ms')
                        if duration > dtmf.TONE_TIME * 0.8:  # ignore if too short signal
                            print(f'ENVELOPE {process.envelopesample:2.1f}')
                            symbol = self.resolvesymbol(
                                process.envelopesample / 3)
                            if symbol:
                                self.key(symbol)
                                # sd.stop()  # Stop playing dial tone
                            process.lastts = t
                        process.signalts = 0
                    continue
                if process.signalts:
                    for g in goertzels:  # update detectors with the sample
                        if not g.ready():  # no need for new samples if already enough
                            # enough samples, store envelope status for thresholding
                            if g.update(sample):
                                process.envelopesample = process.envelope

        process.envelope = 0
        process.signalts = 0
        process.lastts = -dtmf.PAUSE_TIME
        process.envelopesample = 0
        process.ts = 0

        recordfile = open_recordfile()

        istream = sd.InputStream(
            samplerate=SAMPLERATE, blocksize=0, channels=1, callback=callback)
        istream.start()

        while True:
            (ev, params, state) = self.update()
            if state != State.WAIT:
                break
            try:
                while True:
                    data = q.get(False)
                    if recordfile:
                        recordfile.write(data)
                    process(data)
            except queue.Empty:
                pass
        istream.stop()
        istream.close()
        if recordfile:
            recordfile.close()
        sd.stop()
