# pragma once
// clang-format off
// Compression ratio 70.2%%
// 5 unique keys. Key size 3 bits
const uint16_t taps_toneNotesDataHdr[] PROGMEM = {0x2005,0x188,0x20b,0x293,0x30f};
#define taps_toneNotesDataHdrSize 10
const uint8_t taps_toneNotesData[] PROGMEM = {0x20,0x84,0x8,0x41,0x82,0x10,0x60,0x84,0x18,0x21,0x6,0x10,0x62,0x6,0x10,0x20,0x82,0x10};
#define taps_toneNotesDataSize 18
// Compression ratio 55.3%%
// 9 unique keys. Key size 4 bits
const uint16_t taps_toneDurationsDataHdr[] PROGMEM = {0x2009,0x40,0x80,0x100,0x180,0x200,0x400,0x600,0x800};
#define taps_toneDurationsDataHdrSize 18
const uint8_t taps_toneDurationsData[] PROGMEM = {0x41,0x21,0x72,0x41,0x21,0x72,0x41,0x21,0x51,0x41,0x21,0x51,0x41,0x21,0x72,0x31,0x31,0x61,0x51,0x51,0x72,0x41,0x21,0x80};
#define taps_toneDurationsDataSize 24
