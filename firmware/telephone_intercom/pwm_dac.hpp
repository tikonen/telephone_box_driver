// Arduino Nano AtMega328p

// Sample code to drive PWM encoded 20Hz Sine wave on ~600Hz PWM base
// frequncy. PWM output is from Nano pin D9.
// Output can be driven via RC filter to give smoothed out analog output.

#if !defined(ARDUINO_AVR_NANO)
#error "AtMega328p based Arduino board required"
#endif

#define SAMPLE_N 16  // Use power of two for performance!
uint16_t samples[SAMPLE_N];
uint8_t sample_idx = 0;

#define is_pow2(n) (!(n & (n - 1)))

void pwm_dac_disable()
{
    // Disable pin output. Pin reverts to normal digital state.
    TCCR1A = 0;
    // Disable timer interrupt
    TIMSK1 = 0;
}

void pwm_dac_enable()
{
    // Enable pin output and interrupt
    TCCR1A = _BV(COM1A1);
    TIMSK1 = _BV(ICIE1);
}


void pwm_dac_init()
{
    // PWM base frequency is desired final frequency times the
    // number of samples.
    const uint16_t base_freq = SAMPLE_N * TONE_FREQ;

    // Period in seconds is 1/f = 2 * (top * prescaler) / F_CPU
    // => top = F_CPU/( 2 * f * prescaler)
    // Calculate top value for ICR1 register
    // IMPORTANT! The prescaler must be selected so that top is
    // as close to 0xFFFF as possible but not greater.
    const uint16_t counter_top = F_CPU / base_freq / 1 / 2;

    // Precompute samples (PWM duty cycles)
    for (int i = 0; i < SAMPLE_N; i++) {
        samples[i] = round(counter_top * sin(float(M_PI) * i / SAMPLE_N));
    }

    // PWM, Phase and Frequency Correct. ICR1 TOP
    TCCR1A = _BV(COM1A1);
    // 64x prescaler
    // TCCR1B = _BV(WGM13) | _BV(CS11) | _BV(CS10);
    // 8x prescaler
    // TCCR1B = _BV(WGM13) | _BV(CS11);
    // 1x prescaler
    TCCR1B = _BV(WGM13) | _BV(CS10);

    // Initial dac value
    uint16_t dacValue = samples[0];
    OCR1A = dacValue;

    // Generate interrupt on input capture. When the Input Capture Register (ICR1) is
    // set by the WGM1[3:0] to be used as the TOP value, the ICF Flag is set when the
    // counter reaches the TOP value.
    TIMSK1 = _BV(ICIE1);
    // Set input capture register to base frequency
    ICR1 = counter_top;
    // Turn on the output pin D9 (OC1A)
    DDRB |= _BV(1);
    sei();
}

ISR(TIMER1_CAPT_vect)
{
    // Adjust PWM duty cycle
    uint16_t sample = samples[sample_idx++ % SAMPLE_N];
    OCR1A = sample;
}
