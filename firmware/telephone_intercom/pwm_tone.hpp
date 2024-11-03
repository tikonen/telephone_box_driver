#pragma once

inline void tone_init()
{
    TCCR1A = (1 << WGM11) | (1 << COM1A1);
    TCCR1B = (1 << WGM13) | (1 << CS11);
    TIMSK1 = 0;
}

inline void tone_set(unsigned int freq)
{
    if (freq) {
        // Write frequency
        TCNT1 = 0;  // Reset counter
        uint16_t top = F_CPU / 8 / 2 / freq;
        ICR1 = top;       // Set TOP to the period
        OCR1A = top / 2;  // Set compare to half the period

        TCCR1A |= _BV(COM1A1);  // enable output pin
    } else {
        TCCR1A &= ~_BV(COM1A1);  // disable output pin
    }
}
