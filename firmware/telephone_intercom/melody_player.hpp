#pragma once

void melody_init();
void melody_play(const uint16_t* notes, const uint16_t* durations, int n);
void melody_play_encoded(                                              //
    const uint16_t* noteHdr, const uint8_t* notes, uint16_t notesLen,  //
    const uint16_t* durationsHdr, const uint8_t* durations, uint16_t durationsLen);
bool melody_busy();
void melody_stop();