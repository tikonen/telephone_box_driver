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


def load_audio(obj):
    obj.dial_tone = soundfile.read(os.path.join(AUDIO_PATH, DIAL_TONE))
    obj.ringing_tone = soundfile.read(
        os.path.join(AUDIO_PATH, RINGING_TONE))
    obj.low_tone = soundfile.read(os.path.join(AUDIO_PATH, LOW_TONE))
    obj.pickup_effect = soundfile.read(
        os.path.join(AUDIO_PATH, PICKUP_EFFECT))
    obj.hangup_effect = soundfile.read(
        os.path.join(AUDIO_PATH, HANGUP_EFFECT))


def play_audio(effect, loop=True, wait=False):
    if wait:
        loop = False
    sounddevice.play(effect[0], effect[1], loop=loop)
    if wait:
        sounddevice.wait()


def is_playing():
    return sounddevice.get_stream().active


def stop_audio():
    sounddevice.stop()
