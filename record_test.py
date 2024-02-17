import os
import time
import queue

import sounddevice as sd
import soundfile as sf
import numpy

q = queue.Queue()


def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
    q.put(indata.copy())


samplerate = 22050
channels = 1
# run soundfile.available_subtypes('WAV') for list of options
subtype = 'PCM_16'
filename = 'rec_unlimited.wav'


def flush(file):
    """ Write received audio blocks to the record file """
    try:
        while True:
            file.write(q.get(False))
    except queue.Empty:
        pass


 # Make sure the file is opened before recording anything:
with sf.SoundFile(filename, mode='x', samplerate=samplerate,
                  channels=1, subtype=subtype) as file:
    with sd.InputStream(samplerate=samplerate, channels=1, callback=callback):
        print('#' * 80)
        print('press Ctrl+C to stop the recording')
        print('#' * 80)
        while True:
            file.write(q.get())
