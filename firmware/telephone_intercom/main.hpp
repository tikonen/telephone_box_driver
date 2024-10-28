#pragma once

#define VERSION "v1.0"

// -----------------------
// On-board Leds
#define LED_RED_PIN 8

// -----------------------
// Line sense pins
#define SW1_PIN A0
#define SW2_PIN A1
#define LINESENSE1_PIN A7  // Line (analog)
#define LINESENSE2_PIN A6  // Line (analog)
#define TRIPSENSE_PIN 5    // Ring-trip. Active high.

#define LINESENSE_OFFHOOK_V 1.0f

// -----------------------
// Ring generator
#define POWER_DIS_PIN 2
#define RELAY1_EN_PIN 3
#define RELAY2_EN_PIN 4
#define PPA_PIN 6
#define PPB_PIN 7

#define RELAY_DELAY_MS 50

// Trip sense circuit might give initially spurious trips before phone circuit and capacitors have
// reached an stable operation point. Ignore trips for this long.
#define RING_TRIP_STABILIZATION_DELAY_MS 200

#define TONE_DAC_PIN 9
#define TONE_FREQ 425