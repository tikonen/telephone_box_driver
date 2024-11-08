# pragma once
// clang-format off
// Compression ratio 60.2%%
// 34 unique keys. Key size 6 bits
const uint16_t mario_toneNotesDataHdr[] PROGMEM = {0x22,0x61,0x67,0x82,0x92,0x9b,0xa4,0xae,0xb8,0xc3,0xcf,0xdc,0xe9,0xf6,0x105,0x115,0x125,0x149,0x15d,0x171,0x187,0x19f,0x1b8,0x1d2,0x1ed,0x20b,0x24b,0x26e,0x293,0x2ba,0x2e3,0x30f,0x370,0x416};
#define mario_toneNotesDataHdrSize 68
const uint8_t mario_toneNotesData[] PROGMEM = {0x58,0x44,0xdc,0x0,0x44,0xdc,0x0,0x44,0xdc,0x0,0x44,0xd9,0x0,0x44,0xdc,0x1,0x46,0x1f,0x0,0x95,0x9,0x50,0x2,0x51,0x64,0x1,0x8e,0x50,0x0,0xc9,0x44,0x1,0xce,0x58,0x2,0x50,0x60,0x2,0xf,0x5c,0x1,0xce,0x58,0x1,0x8e,0x50,0x3,0x94,0x70,0x4,0x58,0x7c,0x4,0x99,0x80,0x4,0x16,0x74,0x4,0x58,0x7c,0x3,0x96,0x70,0x2,0xd1,0x64,0x3,0x52,0x68,0x2,0x50,0x60,0x2,0x51,0x64,0x1,0x8e,0x50,0x0,0xc9,0x44,0x1,0xce,0x58,0x2,0x50,0x60,0x2,0xf,0x5c,0x1,0xce,0x58,0x1,0x8e,0x50,0x3,0x94,0x70,0x4,0x58,0x7c,0x4,0x99,0x80,0x4,0x16,0x74,0x4,0x58,0x7c,0x3,0x96,0x70,0x2,0xd1,0x64,0x3,0x52,0x68,0x2,0x50,0x60,0x0,0xc0,0x71,0xf7,0x1f,0x0,0x96,0xde,0x1,0xa7,0x5a,0x74,0x6,0x1b,0x61,0xb0,0xe,0x1,0x97,0x19,0x70,0x1,0xc0,0x45,0x54,0x55,0x1,0x25,0x92,0x58,0x3,0x94,0x64,0x3,0x80,0x39,0x63,0x96,0x0,0x74,0x59,0x1,0x26,0x92,0x68,0x0,0xc0,0x71,0xf7,0x1f,0x0,0x66,0xde,0x1,0xa7,0x5a,0x74,0x6,0x1b,0x61,0xb0,0x9,0x0,0xe6,0x5c,0x1,0xd7,0xe1,0x1,0xd7,0xe1,0x1,0xd7,0xe1,0x0,0x90,0x3,0x1,0xc7,0xdc,0x7c,0x2,0x5b,0x78,0x6,0x9d,0x69,0xd0,0x18,0x6d,0x86,0xc0,0x38,0x6,0x5c,0x65,0xc0,0x7,0x1,0x15,0x51,0x54,0x4,0x96,0x49,0x60,0xe,0x51,0x90,0xe,0x0,0xe5,0x8e,0x58,0x1,0xd1,0x64,0x4,0x9a,0x49,0xa0,0x3,0x0,0xa5,0x5b,0x0,0xc4,0x9a,0x0,0xe4,0x59,0x0,0x90,0x9,0x0,0x30,0x3,0x1,0xc7,0xdc,0x7c,0x2,0x5b,0x78,0x6,0x9d,0x69,0xd0,0x18,0x6d,0x86,0xc0,0x38,0x6,0x5c,0x65,0xc0,0x7,0x1,0x15,0x51,0x54,0x4,0x96,0x49,0x60,0xe,0x51,0x90,0xe,0x0,0xe5,0x8e,0x58,0x1,0xd1,0x64,0x4,0x9a,0x49,0xa0,0x3,0x1,0xc7,0xdc,0x7c,0x1,0x9b,0x78,0x6,0x9d,0x69,0xd0,0x18,0x6d,0x86,0xc0,0x24,0x3,0x99,0x70,0x7,0x5f,0x84,0x7,0x5f,0x84,0x7,0x5f,0x84,0x2,0x40,0xc,0x7,0x1f,0x71,0xf0,0x9,0x6d,0xe0,0x1a,0x75,0xa7,0x40,0x61,0xb6,0x1b,0x0,0xe0,0x19,0x71,0x97,0x0,0x1c,0x4,0x55,0x45,0x50,0x12,0x59,0x25,0x80,0x39,0x46,0x40,0x38,0x3,0x96,0x39,0x60,0x7,0x45,0x90,0x12,0x69,0x26,0x80,0xc,0x2,0x95,0x6c,0x3,0x12,0x68,0x3,0x91,0x64,0x2,0x40,0x24,0x0,0xc0,0x9,0x56,0x40,0x55,0x95,0x59,0x0,0x55,0x59,0x1,0x56,0x55,0x64,0x2,0x97,0x68,0x2,0x54,0x70,0x4,0x59,0x45,0x90,0x3,0x45,0x60,0xe,0x50,0xe5,0x0,0x4,0x0,0x95,0x64,0x5,0x59,0x55,0x90,0x5,0x55,0x90,0x15,0x65,0x56,0x40,0x29,0x76,0x80,0x51,0xc5,0x1c,0x0,0x90,0x3,0x0,0x10,0x2,0x55,0x90,0x15,0x65,0x56,0x40,0x15,0x56,0x40,0x55,0x95,0x59,0x0,0xa5,0xda,0x0,0x95,0x1c,0x1,0x16,0x51,0x64,0x0,0xd1,0x58,0x3,0x94,0x39,0x40,0x1,0x0,0x44,0xdc,0x0,0x44,0xdc,0x0,0x44,0xdc,0x0,0x44,0xd9,0x0,0x44,0xdc,0x1,0x46,0x1f,0x0,0x95,0x9,0x50,0x2,0x51,0x64,0x1,0x8e,0x50,0x0,0xc9,0x44,0x1,0xce,0x58,0x2,0x50,0x60,0x2,0xf,0x5c,0x1,0xce,0x58,0x1,0x8e,0x50,0x3,0x94,0x70,0x4,0x58,0x7c,0x4,0x99,0x80,0x4,0x16,0x74,0x4,0x58,0x7c,0x3,0x96,0x70,0x2,0xd1,0x64,0x3,0x52,0x68,0x2,0x50,0x60,0x2,0x51,0x64,0x1,0x8e,0x50,0x0,0xc9,0x44,0x1,0xce,0x58,0x2,0x50,0x60,0x2,0xf,0x5c,0x1,0xce,0x58,0x1,0x8e,0x50,0x3,0x94,0x70,0x4,0x58,0x7c,0x4,0x99,0x80,0x4,0x16,0x74,0x4,0x58,0x7c,0x3,0x96,0x70,0x2,0xd1,0x64,0x3,0x52,0x68,0x2,0x50,0x60,0x0,0xd9,0x70,0x5,0x99,0x59,0x90,0x8,0x45,0x40,0x9,0x0,0xe4,0x55,0x0,0x74,0x96,0x1,0x97,0x59,0x74,0x1,0xc0,0x65,0xd6,0x5d,0x0,0xe4,0x96,0x0,0xe0,0x7,0x0,0x45,0x18,0x1,0xd8,0x1d,0x80,0x7,0x60,0x1d,0xd8,0x7,0x0,0x97,0x60,0x1,0xc7,0xdc,0x7c,0xd6,0x9d,0x69,0xd0,0x9,0x65,0xc0,0x16,0x65,0x66,0x40,0x24,0x4,0x96,0x49,0x60,0xe,0x45,0x40,0xe,0x0,0x90,0x3,0x65,0xc0,0x16,0x65,0x66,0x40,0x21,0x15,0x0,0x24,0x3,0x91,0x54,0x1,0xd2,0x58,0x6,0x5d,0x65,0xd0,0x7,0x1,0x97,0x59,0x74,0x3,0x92,0x58,0x3,0x80,0x1c,0x2,0x54,0x60,0x2,0x5a,0x74,0x2,0x5a,0x74,0x2,0x5a,0x74,0x2,0xd9,0x70,0x3,0x58,0x68,0x3,0x94,0x64,0x4,0x40,0x24,0x4,0x40,0xc,0xe0,0xce,0x0,0x36,0x5c,0x1,0x66,0x56,0x64,0x2,0x11,0x50,0x2,0x40,0x39,0x15,0x40,0x1d,0x25,0x80,0x65,0xd6,0x5d,0x0,0x70,0x19,0x75,0x97,0x40,0x39,0x25,0x80,0x38,0x1,0xc0,0x11,0x46,0x0,0x76,0x7,0x60,0x1,0xd8,0x7,0x76,0x1,0xc0,0x25,0xd8,0x0,0x71,0xf7,0x1f,0x35,0xa7,0x5a,0x74,0x2,0x59,0x70,0x5,0x99,0x59,0x90,0x9,0x1,0x25,0x92,0x58,0x3,0x91,0x50,0x3,0x80,0x24,0x0,0xd9,0x70,0x5,0x99,0x59,0x90,0x8,0x45,0x40,0x9,0x0,0xe4,0x55,0x0,0x74,0x96,0x1,0x97,0x59,0x74,0x1,0xc0,0x65,0xd6,0x5d,0x0,0xe4,0x96,0x0,0xe0,0x7,0x0,0x95,0x18,0x0,0x96,0x9d,0x0,0x96,0x9d,0x0,0x96,0x9d,0x0,0xb6,0x5c,0x0,0xd6,0x1a,0x0,0xe5,0x19,0x1,0x10,0x9,0x1,0x10,0x3,0x38,0x33,0x80,0x9,0x56,0x40,0x55,0x95,0x59,0x0,0x55,0x59,0x1,0x56,0x55,0x64,0x2,0x97,0x68,0x2,0x54,0x70,0x4,0x59,0x45,0x90,0x3,0x45,0x60,0xe,0x50,0xe5,0x0,0x4,0x0,0x95,0x64,0x5,0x59,0x55,0x90,0x5,0x55,0x90,0x15,0x65,0x56,0x40,0x29,0x76,0x80,0x51,0xc5,0x1c,0x0,0x90,0x3,0x0,0x10,0x2,0x55,0x90,0x15,0x65,0x56,0x40,0x15,0x56,0x40,0x55,0x95,0x59,0x0,0xa5,0xda,0x0,0x95,0x1c,0x1,0x16,0x51,0x64,0x0,0xd1,0x58,0x3,0x94,0x39,0x40,0x1,0x0,0x44,0xdc,0x0,0x44,0xdc,0x0,0x44,0xdc,0x0,0x44,0xd9,0x0,0x44,0xdc,0x1,0x46,0x1f,0x0,0x95,0x9,0x50,0x0,0xd9,0x70,0x5,0x99,0x59,0x90,0x8,0x45,0x40,0x9,0x0,0xe4,0x55,0x0,0x74,0x96,0x1,0x97,0x59,0x74,0x1,0xc0,0x65,0xd6,0x5d,0x0,0xe4,0x96,0x0,0xe0,0x7,0x0,0x45,0x18,0x1,0xd8,0x1d,0x80,0x7,0x60,0x1d,0xd8,0x7,0x0,0x97,0x60,0x1,0xc7,0xdc,0x7c,0xd6,0x9d,0x69,0xd0,0x9,0x65,0xc0,0x16,0x65,0x66,0x40,0x24,0x4,0x96,0x49,0x60,0xe,0x45,0x40,0xe,0x0,0x90,0x3,0x65,0xc0,0x16,0x65,0x66,0x40,0x21,0x15,0x0,0x24,0x3,0x91,0x54,0x1,0xd2,0x58,0x6,0x5d,0x65,0xd0,0x7,0x1,0x97,0x59,0x74,0x3,0x92,0x58,0x3,0x80,0x1c,0x2,0x54,0x60,0x2,0x5a,0x74,0x2,0x5a,0x74,0x2,0x5a,0x74,0x2,0xd9,0x70,0x3,0x58,0x68,0x3,0x94,0x64,0x4,0x40,0x24,0x4,0x40,0xc,0xe0,0xce};
#define mario_toneNotesDataSize 1119
// Compression ratio 74.1%%
// 13 unique keys. Key size 4 bits
const uint16_t mario_toneDurationsDataHdr[] PROGMEM = {0xd,0xf,0x14,0x2f,0x5e,0x5f,0xbd,0xbe,0xc8,0x14c,0x14d,0x1d9,0x1db};
#define mario_toneDurationsDataHdrSize 26
const uint8_t mario_toneDurationsData[] PROGMEM = {0x82,0x22,0x32,0x22,0x62,0x22,0x72,0x22,0x32,0x22,0x72,0x22,0xc2,0x22,0x2b,0x22,0x29,0x22,0x29,0x22,0x29,0x22,0x26,0x22,0x26,0x22,0x23,0x22,0x27,0x22,0x25,0x22,0x25,0x22,0x25,0x22,0x27,0x22,0x23,0x22,0x26,0x22,0x26,0x22,0x23,0x22,0x23,0x22,0x29,0x22,0x29,0x22,0x29,0x22,0x29,0x22,0x26,0x22,0x26,0x22,0x23,0x22,0x27,0x22,0x25,0x22,0x25,0x22,0x25,0x22,0x27,0x22,0x23,0x22,0x26,0x22,0x26,0x22,0x23,0x22,0x23,0x22,0x29,0x57,0x22,0x22,0x32,0x22,0x32,0x22,0x23,0x22,0x22,0x35,0x32,0x22,0x23,0x53,0x22,0x22,0x32,0x22,0x23,0x22,0x23,0x53,0x22,0x22,0x32,0x22,0x32,0x22,0x23,0x57,0x22,0x22,0x32,0x22,0x32,0x22,0x23,0x22,0x22,0x35,0x32,0x22,0x62,0x22,0x62,0x22,0x32,0x22,0x75,0x75,0x72,0x22,0x23,0x22,0x23,0x22,0x22,0x32,0x22,0x23,0x53,0x22,0x22,0x35,0x32,0x22,0x23,0x22,0x22,0x32,0x22,0x35,0x32,0x22,0x23,0x22,0x23,0x22,0x22,0x35,0x72,0x22,0x92,0x22,0x92,0x22,0x94,0x35,0x75,0x75,0x72,0x22,0x23,0x22,0x23,0x22,0x22,0x32,0x22,0x23,0x53,0x22,0x22,0x35,0x32,0x22,0x23,0x22,0x22,0x32,0x22,0x35,0x32,0x22,0x23,0x22,0x23,0x22,0x22,0x35,0x72,0x22,0x23,0x22,0x23,0x22,0x22,0x32,0x22,0x23,0x53,0x22,0x26,0x22,0x26,0x22,0x23,0x22,0x27,0x57,0x57,0x22,0x22,0x32,0x22,0x32,0x22,0x23,0x22,0x22,0x35,0x32,0x22,0x23,0x53,0x22,0x22,0x32,0x22,0x23,0x22,0x23,0x53,0x22,0x22,0x32,0x22,0x32,0x22,0x23,0x57,0x22,0x29,0x22,0x29,0x22,0x29,0x43,0x57,0x57,0x22,0x23,0x22,0x22,0x62,0x22,0x72,0x22,0x23,0x22,0x27,0x22,0x23,0x22,0x22,0x72,0x22,0x32,0x22,0x26,0x56,0x22,0x23,0x22,0x22,0x62,0x22,0x72,0x22,0x23,0x22,0x23,0x22,0x22,0x35,0xa5,0x95,0x62,0x22,0x32,0x22,0x26,0x22,0x27,0x22,0x22,0x32,0x22,0x72,0x22,0x32,0x22,0x27,0x22,0x23,0x22,0x22,0x65,0x62,0x22,0x32,0x22,0x62,0x22,0x72,0x22,0x32,0x22,0x72,0x22,0xc2,0x22,0x2b,0x22,0x29,0x22,0x29,0x22,0x29,0x22,0x26,0x22,0x26,0x22,0x23,0x22,0x27,0x22,0x25,0x22,0x25,0x22,0x25,0x22,0x27,0x22,0x23,0x22,0x26,0x22,0x26,0x22,0x23,0x22,0x23,0x22,0x29,0x22,0x29,0x22,0x29,0x22,0x29,0x22,0x26,0x22,0x26,0x22,0x23,0x22,0x27,0x22,0x25,0x22,0x25,0x22,0x25,0x22,0x27,0x22,0x23,0x22,0x26,0x22,0x26,0x22,0x23,0x22,0x23,0x22,0x29,0x22,0x23,0x22,0x22,0x72,0x22,0x35,0x72,0x22,0x72,0x22,0x32,0x22,0x23,0x53,0x22,0x22,0x32,0x22,0x34,0x35,0x72,0x22,0x52,0x22,0x25,0x22,0x11,0x13,0x32,0x22,0x52,0x22,0x25,0x22,0x22,0x52,0x22,0x32,0x22,0x23,0x53,0x22,0x22,0x32,0x22,0x34,0x35,0x72,0x22,0x32,0x22,0x27,0x22,0x23,0x57,0x22,0x27,0x22,0x23,0x22,0x22,0x35,0x32,0x22,0x23,0x22,0x23,0x43,0x57,0x22,0x23,0x22,0x27,0x22,0x23,0x22,0x25,0x22,0x25,0x22,0x25,0x22,0x23,0x53,0x53,0x53,0x22,0x22,0xc2,0x22,0x32,0x22,0x27,0x22,0x23,0x57,0x22,0x27,0x22,0x23,0x22,0x22,0x35,0x32,0x22,0x23,0x22,0x23,0x43,0x57,0x22,0x25,0x22,0x22,0x52,0x21,0x11,0x33,0x22,0x25,0x22,0x22,0x52,0x22,0x25,0x22,0x23,0x22,0x22,0x35,0x32,0x22,0x23,0x22,0x23,0x43,0x57,0x22,0x23,0x22,0x22,0x72,0x22,0x35,0x72,0x22,0x72,0x22,0x32,0x22,0x23,0x53,0x22,0x22,0x32,0x22,0x34,0x35,0x72,0x22,0x32,0x22,0x72,0x22,0x32,0x22,0x52,0x22,0x52,0x22,0x52,0x22,0x35,0x35,0x35,0x32,0x22,0x2c,0x22,0x23,0x22,0x22,0x62,0x22,0x72,0x22,0x23,0x22,0x27,0x22,0x23,0x22,0x22,0x72,0x22,0x32,0x22,0x26,0x56,0x22,0x23,0x22,0x22,0x62,0x22,0x72,0x22,0x23,0x22,0x23,0x22,0x22,0x35,0xa5,0x95,0x62,0x22,0x32,0x22,0x26,0x22,0x27,0x22,0x22,0x32,0x22,0x72,0x22,0x32,0x22,0x27,0x22,0x23,0x22,0x22,0x65,0x62,0x22,0x32,0x22,0x62,0x22,0x72,0x22,0x32,0x22,0x72,0x22,0xc2,0x22,0x2b,0x22,0x23,0x22,0x22,0x72,0x22,0x35,0x72,0x22,0x72,0x22,0x32,0x22,0x23,0x53,0x22,0x22,0x32,0x22,0x34,0x35,0x72,0x22,0x52,0x22,0x25,0x22,0x11,0x13,0x32,0x22,0x52,0x22,0x25,0x22,0x22,0x52,0x22,0x32,0x22,0x23,0x53,0x22,0x22,0x32,0x22,0x34,0x35,0x72,0x22,0x32,0x22,0x27,0x22,0x23,0x57,0x22,0x27,0x22,0x23,0x22,0x22,0x35,0x32,0x22,0x23,0x22,0x23,0x43,0x57,0x22,0x23,0x22,0x27,0x22,0x23,0x22,0x25,0x22,0x25,0x22,0x25,0x22,0x23,0x53,0x53,0x53,0x22,0x22};
#define mario_toneDurationsDataSize 746
