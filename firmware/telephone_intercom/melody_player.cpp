#include <Arduino.h>

#include "melody_player.hpp"
#include "pwm_tone.hpp"

union CompressedMelodyHeader {
    struct {
        uint8_t numkeys;
        uint8_t : 5;
        uint8_t padding : 3;  // number of filler keys on the last byte
    };
    uint16_t b;
};

struct CompressedData {
    const uint16_t* hdrdata;
    const uint8_t* data;
    uint16_t len;

    uint16_t enc;
    uint8_t avail;
    uint16_t idx;
    uint8_t keymask;
    uint8_t keybits;

    void init(const uint16_t* enchdr, const uint8_t* encdata, uint16_t datalen)
    {
        hdrdata = enchdr;
        data = encdata;
        len = datalen;

        enc = 0;
        avail = 0;
        idx = 0;
        keymask = 0;
        keybits = 1;

        CompressedMelodyHeader hdr;
        hdr.b = pgm_read_word_near(hdrdata);
        // compute keymask and number of bits
        int tmp = 2;
        while (tmp < hdr.numkeys) {
            tmp *= 2;
            keybits++;
        }
        keymask = tmp - 1;
    }

    inline bool decode(uint16_t* outv)
    {
        while (true) {
            if (avail >= keybits) {
                uint8_t key = enc >> (avail - keybits);
                key &= keymask;
                if (key) {
                    *outv = pgm_read_word_near(hdrdata + key);
                } else {
                    *outv = 0;
                }
                avail -= keybits;
                return true;
            }
            if (idx < len) {
                enc <<= 8;
                enc |= pgm_read_byte_near(data + idx++);
                avail += 8;
                continue;
            }
            return false;
        }
    }
};

static CompressedData melodyNotes;
static CompressedData melodyDurations;

struct PlainMelodyData {
    const uint16_t* notesData = NULL;
    const uint16_t* durationsData = NULL;
    uint16_t len = 0;
    uint16_t idx = 0;

    void init(const uint16_t* notes, const uint16_t* durations, uint16_t datalen)
    {
        notesData = notes;
        durationsData = durations;
        len = datalen;
        idx = 0;
    }

    inline bool decode(uint16_t* note, uint16_t* duration)
    {
        if (idx < len) {
            *note = pgm_read_word_near(notesData + idx);
            *duration = pgm_read_word_near(durationsData + idx);
            idx++;
            return true;
        }
        return false;
    }
};

static PlainMelodyData plainMelody;

void melody_init()
{
    TIMSK2 = 0;

    // PWM Phase correct
    TCCR2A = _BV(WGM20);
    // 64 prescaler
    // TCCR2B = _BV(WGM22) | _BV(CS22) | _BV(CS20);
    // 32 prescaler
    TCCR2B = _BV(WGM22) | _BV(CS21) | _BV(CS20);

    // 8-bit Timer maximum counter value is 255. Prescaler must be large enough to keep
    // TOP below that.
    // interrupt each 1ms. TOP = F_CPU / prescaler / Hz / 2.
    // TOP = F_CPU / 32 / 1000 / 2 = 250
    OCR2A = F_CPU / 32 / 1000 / 2;

    tone_init();
}

void melody_play_blocking(const uint16_t* notes, const uint16_t* durations, int n)
{
    tone_init();
    for (int i = 0; i < n; i++) {
        uint16_t note = pgm_read_word_near(notes + i);
        if (note) {
            tone_set(note);
            // tone(9, note);
        } else {
            tone_set(0);
            // noTone(9);
        }
        delay(pgm_read_word_near(durations + i));
    }
    tone_set(0);
}

bool melody_busy() { return TIMSK2; }

void melody_stop()
{
    TIMSK2 = 0;
    TCNT2 = 0;
    tone_set(0);
}

static bool plain_decode(uint16_t* tone, uint16_t* delay) { return plainMelody.decode(tone, delay); }
static bool compressed_decode(uint16_t* tone, uint16_t* delay) { return melodyNotes.decode(tone) && melodyDurations.decode(delay); }

static bool (*decoder)(uint16_t* tone, uint16_t* delay);

static uint16_t elapsedms = 0;
static uint16_t noteDurationms = 0;

void melody_play_encoded(                                              //
    const uint16_t* noteHdr, const uint8_t* notes, uint16_t notesLen,  //
    const uint16_t* durationsHdr, const uint8_t* durations, uint16_t durationsLen)
{
    melody_stop();

    melodyNotes.init(noteHdr, notes, notesLen);
    melodyDurations.init(durationsHdr, durations, durationsLen);

    elapsedms = 0;
    noteDurationms = 0;

    decoder = compressed_decode;

    // overflow interrupt enable
    TIMSK2 = _BV(TOIE2);
}

void melody_play(const uint16_t* notes, const uint16_t* durations, int n)
{
    melody_stop();

    plainMelody.init(notes, durations, n);

    elapsedms = 0;
    noteDurationms = 0;

    decoder = plain_decode;

    // overflow interrupt enable
    TIMSK2 = _BV(TOIE2);
}

ISR(TIMER2_OVF_vect)
{
    // Overflow interrupt is triggered in 1ms intervals.
    elapsedms++;

    if (elapsedms >= noteDurationms) {
        elapsedms = 0;
        uint16_t tone;
        uint16_t delay;
        if (decoder(&tone, &delay)) {
            tone_set(tone);
            noteDurationms = delay;
        } else {
            melody_stop();
        }
    }
}
