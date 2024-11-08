# pragma once
// clang-format off
// Compression ratio 30.4%%
// 10 unique keys. Key size 4 bits
const uint16_t beverly_toneNotesDataHdr[] PROGMEM = {0x200a,0x1ee,0x24b,0x293,0x2e4,0x310,0x370,0x3dc,0x417,0x526};
#define beverly_toneNotesDataHdrSize 20
const uint8_t beverly_toneNotesData[] PROGMEM = {0x35,0x33,0x63,0x23,0x73,0x38,0x75,0x37,0x93,0x22,0x14,0x30};
#define beverly_toneNotesDataSize 12
// Compression ratio 58.7%%
// 5 unique keys. Key size 3 bits
const uint16_t beverly_toneDurationsDataHdr[] PROGMEM = {0x2005,0x6e,0xe6,0x154,0x1cc};
#define beverly_toneDurationsDataHdrSize 10
const uint8_t beverly_toneDurationsData[] PROGMEM = {0x8d,0x14,0x94,0x68,0xa4,0x92,0x45,0x14,0xa0};
#define beverly_toneDurationsDataSize 9
