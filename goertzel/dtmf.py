
# DTMF low and high frequencies (Hz)
FREQ_LOW1 = 697
FREQ_LOW2 = 770
FREQ_LOW3 = 852
FREQ_LOW4 = 941
FREQ_HIGH1 = 1209
FREQ_HIGH2 = 1336
FREQ_HIGH3 = 1477
FREQ_HIGH4 = 1633

TONE_TIME = 70e-3  # minimum tone duration (s)
PAUSE_TIME = 30e-3  # minimum pause between tones (s)

SYMBOLS = [  # 0, 1, ... 9, #, *
    ('1', (FREQ_LOW1, FREQ_HIGH1)),
    ('2', (FREQ_LOW1, FREQ_HIGH2)),
    ('3', (FREQ_LOW1, FREQ_HIGH3)),
    ('4', (FREQ_LOW2, FREQ_HIGH1)),
    ('5', (FREQ_LOW2, FREQ_HIGH2)),
    ('6', (FREQ_LOW2, FREQ_HIGH3)),
    ('7', (FREQ_LOW3, FREQ_HIGH1)),
    ('8', (FREQ_LOW3, FREQ_HIGH2)),
    ('9', (FREQ_LOW3, FREQ_HIGH3)),
    ('*', (FREQ_LOW4, FREQ_HIGH1)),
    ('0', (FREQ_LOW4, FREQ_HIGH2)),
    ('#', (FREQ_LOW4, FREQ_HIGH3))
]

ALL_SYMBOLS = [  # 0, 1, ... 9, #, *, A, B, C, D
    ('1', (FREQ_LOW1, FREQ_HIGH1)),
    ('2', (FREQ_LOW1, FREQ_HIGH2)),
    ('3', (FREQ_LOW1, FREQ_HIGH3)),
    ('A', (FREQ_LOW1, FREQ_HIGH4)),
    ('4', (FREQ_LOW2, FREQ_HIGH1)),
    ('5', (FREQ_LOW2, FREQ_HIGH2)),
    ('6', (FREQ_LOW2, FREQ_HIGH3)),
    ('B', (FREQ_LOW2, FREQ_HIGH4)),
    ('7', (FREQ_LOW3, FREQ_HIGH1)),
    ('8', (FREQ_LOW3, FREQ_HIGH2)),
    ('9', (FREQ_LOW3, FREQ_HIGH3)),
    ('C', (FREQ_LOW3, FREQ_HIGH4)),
    ('*', (FREQ_LOW4, FREQ_HIGH1)),
    ('0', (FREQ_LOW4, FREQ_HIGH2)),
    ('#', (FREQ_LOW4, FREQ_HIGH3)),
    ('D', (FREQ_LOW4, FREQ_HIGH4))
]
