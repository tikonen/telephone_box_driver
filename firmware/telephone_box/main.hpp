#pragma once

#define VERSION "v2.0"

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

// Ringing parameters
#define RING_FREQ_HZ 25
#define RING_CADENCE_ON_MS 2000
#define RING_CADENCE_OFF_MS 2000

#define TEST_BUTTON_PIN 2
