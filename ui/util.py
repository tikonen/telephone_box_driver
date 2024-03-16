
import queue
import numpy as np
import sounddevice as sd


class Box:  # Helper class
    __init__ = lambda self, **kw: setattr(self, '__dict__', kw)


class StreamAudioPlayer():
    def __init__(self, samplerate, channels, dtype='float32'):
        self.samplerate = samplerate
        self.channels = channels
        self.dtype = dtype
        self.blocksize = 1024

    def start_audio(self):
        self.q = queue.Queue()

        def callback(outdata, frames, time, status):
            if not self.q.empty():
                data = self.q.get_nowait()
                outdata[:] = data
            else:
                outdata.fill(0)

        self.outs = sd.OutputStream(
            samplerate=self.samplerate, dtype=self.dtype, latency=0.1, blocksize=self.blocksize, channels=self.channels, callback=callback)
        self.outs.start()

    def queue_audio(self, sample, repeats):
        blocksize = self.blocksize
        audiodata = np.concatenate(
            [sample for _ in range(0, repeats)], dtype=self.dtype)
        audiodata = audiodata.reshape(-1, 1)
        for idx in range(blocksize, len(audiodata), blocksize):
            self.q.put(audiodata[idx-blocksize:idx])

        rem = len(audiodata) % blocksize
        if rem:
            block = np.zeros((blocksize, 1), dtype=audiodata.dtype)
            block[:rem] = audiodata[len(audiodata) - rem:]
            self.q.put(block)

    def clear_audio(self):
        self.q = queue.Queue()
