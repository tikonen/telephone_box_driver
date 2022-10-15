#pragma once

#define VERSION "v0.2"

// -----------------------
// On-board Leds
#define LED_YELLOW A1
#define LED_RED 2
#define LED_GREEN 3

#define LED_DEBUG LED_YELLOW

// -----------------------
// Line sense pins
#define LSENSE_PIN A0  // Line
#define PSENSE_PIN A4  // Ring-trip

// -----------------------
// Ring generator
#define HB_OUT1_PIN 5
#define HB_OUT2_PIN 6
#define RING_EN_PIN A5
#define PWM_PIN 9
#define RELAY_DELAY_MS 50

// Ringing parameters
#define RING_FREQ_HZ 20
#define RING_PWM_DUTY 0.3
#define RING_TIMEMS 2000
#define RING_PAUSEMS 2000

#define TEST_BUTTON_PIN 10
