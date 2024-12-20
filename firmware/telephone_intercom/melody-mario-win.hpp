#pragma once
// Uncompressed data. ratio -5.6% (compression would be -13.0%)
const uint8_t mariowin_toneNotes[] PROGMEM = {0xff,0x82,0x00,0x06,0x01,0x4a,0x01,0x88,0x01,0x0b,0x02,0x94,0x02,0x10,0x03,0x94,0x02,0x92,0x00,0x06,0x01,0x37,0x01,0x9f,0x01,0x0b,0x02,0x6e,0x02,0x3f,0x03,0x6e,0x02,0x9b,0x00,0x26,0x01,0x5d,0x01,0xd2,0x01,0x4c,0x02,0xbb,0x02,0xa5,0x03,0xa5,0x03,0xa5,0x03,0xa5,0x03,0x17,0x04};
#define mariowin_toneNotesSize 55
// Compression ratio 68.5%
// 4 unique keys. Key size 2 bits
const uint8_t mariowin_toneDurations[] PROGMEM = {0x04,0x20,0x64,0x00,0x2c,0x01,0x90,0x01,0x07,0x00,0x55,0x5a,0x55,0x5a,0x55,0x59,0x5c};
#define mariowin_toneDurationsHdrSize 8
#define mariowin_toneDurationsEncSize 7
#define mariowin_toneDurationsSize 17
