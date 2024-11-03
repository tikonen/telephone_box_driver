#include <Arduino.h>

#include "melody_player.hpp"
#include "pwm_tone.hpp"

static const uint16_t* playingNotes;
static const uint16_t* playingNoteDurations;
static uint16_t playingNoteCount;
static uint16_t playingIdx;

void melody_init()
{
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

    playingNotes = NULL;
    playingNoteDurations = NULL;
    playingNoteCount = 0;
    playingIdx = 0;

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

void melody_play(const uint16_t* notes, const uint16_t* durations, int n)
{
    TIMSK2 = 0;
    TCNT2 = 0;


    playingNotes = notes;
    playingNoteDurations = durations;
    playingNoteCount = n;
    playingIdx = 0;

    // overflow interrupt enable
    TIMSK2 = _BV(TOIE2);
}

bool melody_busy() { return TIMSK2; }

void melody_stop()
{
    TIMSK2 = 0;
    tone_set(0);
}

ISR(TIMER2_OVF_vect)
{
    static uint16_t mscount = 0;
    static uint16_t noteDuration = 0;

    mscount++;

    if (mscount >= noteDuration) {
        mscount = 0;
        if (playingIdx >= playingNoteCount) {
            playingIdx = 0;
            TIMSK2 = 0;
            return;
        }

        tone_set(pgm_read_word_near(playingNotes + playingIdx));
        noteDuration = pgm_read_word_near(playingNoteDurations + playingIdx);
        playingIdx++;
    }
}
