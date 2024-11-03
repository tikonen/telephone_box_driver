#pragma once

void melody_init();
void melody_play(const uint16_t* notes, const uint16_t* durations, int n);
bool melody_busy();
void melody_stop();