#include <Arduino.h>

#include "melody_player.hpp"
#include "pwm_tone.hpp"

#define UNCOMPRESSED_PLAYER 0

//
// Decode bit-packed lookup-table compressed data.
//
// Data format
//
// Header contains number of keys and key to value map. Zero key is implicit as its value is always 0.
// 1B: reserved
// 1B: number of keys
// 2B: key 1 16-bit value
// 2B: key 2 16-bit value
// ...
// 2B: compressed data
// 1B: Data0
// 1B: Data1
// ..
//
// Bit packed key values. Final byte padded with 0's. Key width in bits is ceil(log2(number of keys))
//
// For example with 3 bit key (max. 7 possible values)
// [       byte 0x64   |        byte 0x78    | ..
// [0 1 1 | 0 0 1 | 0 0 0 | 1 1 1 | 1 0 0 | 0 0 0 | ...
// [ k:3  |  k:1  |  k:0  | k:7   | k:4   | k:0   | ..
//
// byte sequence 0x64, 0x78 would be decoded to key value list 3, 1, 0, 7, 4, ...
// Decode looks up the values from the header table.
//
struct CompressedData {
    const uint16_t* hdrdata;
    const uint8_t* encdata;
    uint16_t len;

    uint16_t enc;
    uint16_t idx;
    uint8_t avail;
    uint8_t keymask;
    uint8_t keybits;

    union CompressedHeader {
        struct {
            uint8_t numkeys;
            uint8_t : 5;
            uint8_t padding : 3;  // number of filler keys on the last byte
        };
        uint16_t b;
    };


    void init(const uint8_t* packet)
    {
        hdrdata = (const uint16_t*)packet;

        enc = 0;
        avail = 0;
        idx = 0;
        keymask = 0;
        keybits = 1;

        CompressedHeader hdr;
        hdr.b = pgm_read_word_near(hdrdata);

        if (hdr.numkeys == 0xFF) {
            // data is uncompressed
            len = pgm_read_word_near(packet + 1);
            encdata = packet + 3;
            keybits = 0;
        } else {
            // compute keymask and number of bits
            int tmp = 2;
            while (tmp < hdr.numkeys) {
                tmp *= 2;
                keybits++;
            }
            keymask = tmp - 1;

            // get data len and set pointer to start of encoded data
            len = pgm_read_word_near(hdrdata + hdr.numkeys);
            encdata = packet + 2 * (hdr.numkeys + 1);
        }
    }

    inline bool decode(uint16_t* outv)
    {
        if (keybits) {
            while (true) {
                if (avail >= keybits) {
                    // TODO Check padding value for the last bytes. Extra values due to byte padding are currently returned as 0.
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
                    enc |= pgm_read_byte_near(encdata + idx++);
                    avail += 8;
                    continue;
                }
                return false;
            }
        } else {
            // uncompressed data
            if (idx < len) {
                *outv = pgm_read_word_near((uint16_t*)encdata + idx++);
                return true;
            }
        }
        return false;
    }
};

struct CompressedMelody {
    CompressedData notes;
    CompressedData durations;

    void init(const uint8_t* toneData, const uint8_t* durationsData)
    {
        notes.init(toneData);
        durations.init(durationsData);
    }
    inline bool decode(uint16_t* note, uint16_t* duration) { return notes.decode(note) && durations.decode(duration); }
};

static CompressedMelody encodedMelody;

struct PlainMelody {
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

#if UNCOMPRESSED_PLAYER
static PlainMelody plainMelody;
#endif

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

bool melody_busy() { return TIMSK2; }

void melody_stop()
{
    TIMSK2 = 0;
    TCNT2 = 0;
    tone_set(0);
}

static uint16_t elapsedms = 0;
static uint16_t noteDurationms = 0;

#if UNCOMPRESSED_PLAYER
static bool plain_decode(uint16_t* tone, uint16_t* delay) { return plainMelody.decode(tone, delay); }
static bool compressed_decode(uint16_t* tone, uint16_t* delay) { return encodedMelody.decode(tone, delay); }

static bool (*decoder)(uint16_t* tone, uint16_t* delay);

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
#else
static inline bool decoder(uint16_t* tone, uint16_t* delay) { return encodedMelody.decode(tone, delay); }
#endif

void melody_play_encoded(const uint8_t* toneData, const uint8_t* durationsData)
{
    melody_stop();

    encodedMelody.init(toneData, durationsData);

    elapsedms = 0;
    noteDurationms = 0;

#if UNCOMPRESSED_PLAYER
    decoder = compressed_decode;
    // decoder = [](uint16_t* tone, uint16_t* delay) { return encodedMelody.decode(tone, delay); };
#endif
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
