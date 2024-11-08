#pragma once

void melody_init();
void melody_play(const uint16_t* notes, const uint16_t* durations, int n);
void melody_play_encoded(const uint8_t* toneData, const uint8_t* durationsData);
bool melody_busy();
void melody_stop();