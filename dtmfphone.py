import sys
import queue

import sounddevice as sd
import soundfile as sf

from telephonebox import State, Command, Event
from basicphone import BasicPhone
from dtmfdecoder import DTFMDecoder

# DEBUG_RECORD='dtmf_demo_rec.wav'
DEBUG_RECORD = None
SAMPLERATE = 14400


def open_recordfile(filename):
    if filename:
        print("Recording to", filename)
        # open soundfile and start recording until user hangs up
        return sf.SoundFile(filename, mode='w', samplerate=SAMPLERATE, channels=1, subtype='PCM_16')
    return None


class DTMFPhone(BasicPhone):

    def __init__(self, port, verbose):
        super().__init__(port, verbose)
        self.verbose = verbose
        # Configure dial mode to none
        self.config({'DM': 0})

    def key(self, symbol):
        sd.stop()
        print(f'KEY {symbol}')

    # Phone is off-hook
    def wait(self):
        print("*** WAIT (OFFHOOK)")
        sd.play(self.dial_tone[0], self.dial_tone[1], loop=True)

        decoder = DTFMDecoder(self.verbose, SAMPLERATE)

        # Setup audio input and start monitoring dialed numbers
        q = queue.Queue()

        def callback(indata, frames, time, status):
            """Called (from a separate thread) for each audio block."""
            if status:
                print(status, file=sys.stderr)
            q.put(indata.copy())

        recordfile = open_recordfile(DEBUG_RECORD)

        # For some reason Python sounddevice recorded audio can be -6dB compared to e.g. Audacity 100% recording level.
        # I suspect it's caused by forcing a mono recording from a stereo device. See https://github.com/PortAudio/portaudio/issues/397
        # Stereo device produces mono signal by summing and halving to avoid clipping.  M = (L + R)/2
        istream = sd.InputStream(
            samplerate=SAMPLERATE, blocksize=0, channels=1, callback=callback)
        istream.start()
        decoder.start()

        def process_data():
            while not q.empty():
                data = q.get_nowait()
                if recordfile:
                    recordfile.write(data)
                decoder.process(data, lambda symbol: self.key(symbol))

        while True:
            (ev, params, state) = self.update()
            if state != State.WAIT:
                break

            process_data()

        istream.stop()
        istream.close()
        if recordfile:
            recordfile.close()
        sd.stop()
