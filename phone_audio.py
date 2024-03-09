import os
import sounddevice
import soundfile


# Precise tone plan is a signaling specification for plain old telephone
# system (PSTN) that defines the call progress tones used on line.
AUDIO_PATH = './audio'
DIAL_TONE = 'tones/euro/dialtone_europe_425.wav'
RINGING_TONE = 'tones/euro/ringing_tone_europe_425_cadence.wav'
LOW_TONE = 'tones/precise_tone_plan/low_tone_480_620_cadence.wav'  # busy/error tone
HIGH_TONE = 'tones/precise_tone_plan/high_tone_480.wav'
PICKUP_EFFECT = 'phone_pickup.wav'
HANGUP_EFFECT = 'phone_hangup.wav'
DTMF_EFFECTS = 'tones/dtmf/dtmf_{symbol}.wav'


def load_file(file):
    return soundfile.read(os.path.join(
        AUDIO_PATH, file), dtype='float32')


def load_audio(obj):
    obj.dial_tone = soundfile.read(os.path.join(
        AUDIO_PATH, DIAL_TONE), dtype='float32')
    obj.ringing_tone = soundfile.read(
        os.path.join(AUDIO_PATH, RINGING_TONE), dtype='float32')
    obj.low_tone = soundfile.read(os.path.join(
        AUDIO_PATH, LOW_TONE), dtype='float32')
    obj.pickup_effect = soundfile.read(
        os.path.join(AUDIO_PATH, PICKUP_EFFECT), dtype='float32')
    obj.hangup_effect = soundfile.read(
        os.path.join(AUDIO_PATH, HANGUP_EFFECT), dtype='float32')


def create_dtmf_player():
    # Load DTMF audio files
    SAMPLERATE = 8000
    dtmf = {}
    symbols = [str(s) for s in range(0, 10)] + ['A', 'B', 'C', 'D']
    path = os.path.join(AUDIO_PATH, DTMF_EFFECTS)
    for symbol in symbols:
        dtmf[symbol] = soundfile.read(
            path.format(symbol=symbol), dtype='float32')
    dtmf['#'] = soundfile.read(path.format(symbol='hash'), dtype='float32')
    dtmf['*'] = soundfile.read(path.format(symbol='star'), dtype='float32')

    # Check sample rate and clean
    for k in dtmf.keys():
        samplerate = dtmf[k][1]
        if samplerate != SAMPLERATE:
            print(
                f'WARNING: Invalid DTMF "{k}" samplerate {samplerate}. Expected {SAMPLERATE}')
        dtmf[k] = dtmf[k][0]

    class DTMFPlayer():
        def __init__(self):
            self.outs = sounddevice.OutputStream(
                SAMPLERATE, dtype='float32', blocksize=0, channels=1)

        def start(self):
            self.outs.start()

        def stop(self):
            self.outs.stop()

        def beep(self, key):
            self.outs.write(dtmf[key])

    return DTMFPlayer()


def play_audio(effect, loop=True, wait=False):
    sounddevice.play(effect[0], effect[1], loop=loop and not wait)
    if wait:
        sounddevice.wait()


def is_playing():
    return sounddevice.get_stream().active


def stop_audio():
    sounddevice.stop()
