#pragma once

#define VERSION "v2.1"

// -----------------------
// On-board Leds
#define LED_RED_PIN 10
#define LED_YELLOW_PIN 11

// -----------------------
// Line sense pins
#define LINESENSE_PIN A0  // Line (analog)
#define TRIPSENSE_PIN 9   // Ring-trip. Active high.

// -----------------------
// Ring generator
#define PPA_PIN 7
#define PPB_PIN 8
#define RELAY_EN_PIN 4
#define POWER_DIS_PIN 5
#define RELAY_DELAY_MS 50

// Trip sense circuit might give initially spurious trips before phone circuit and capacitors have
// reached an stable operation point. Ignore trips for this long.
#define RING_TRIP_STABILIZATION_DELAY_MS 200

#define TEST_BUTTON_PIN 2
