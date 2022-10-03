#include <Arduino.h>

#include "serial_cmd.hpp"

// Ring buffer length should be power of 2 so that the compiler can optimize the
// expensive modulo division to simple bitwise AND
#define RING_BUFFER_LEN 32

struct RingBuffer {
    char data[RING_BUFFER_LEN];
    uint8_t ridx;
    uint8_t widx;

    inline char& operator[](unsigned int idx) { return data[idx % RING_BUFFER_LEN]; }

    void clear()
    {
        ridx = 0;
        widx = 0;
    }
};

static RingBuffer recvRingBuffer;

#define LINE_BUFFER_LEN 16
static char linebuffer[LINE_BUFFER_LEN];

void serial_clear()
{
    recvRingBuffer.clear();
    while (Serial.available()) Serial.read();
}

static inline int serial_available(struct RingBuffer& rb)
{
    // Unsigned arithmentic ensures that available bytes is correct even
    // when the widx has rolled back to the beginning and is smaller than ridx.
    // e.g. 0 - 255 => 1, 1 - 254 => 3, 253 - 254 => 255 etc..
    // The result must be type casted for this to work.
    int available = (uint8_t)(rb.widx - rb.ridx);
    return available;
}

// parse lines separated by carriage return and a newline (\r\n)
static char* parse_line(struct RingBuffer& rb)
{
    const int available = serial_available(rb);

    for (int i = 0; i < available - 1; i++) {
        if (rb[i + rb.ridx] == '\r' && rb[i + rb.ridx + 1] == '\n') {
            // found end of line sequence (\r\n), copy line data (if any)
            int idx = 0;
            while (i-- > 0) {
                char c = rb[rb.ridx++];

                // check for target buffer overflow and copy character
                if (idx < LINE_BUFFER_LEN - 1) {
                    linebuffer[idx++] = c;
                }
            }
            // terminate string and clear trailing whitespace
            do {
                linebuffer[idx--] = '\0';
            } while (idx >= 0 && linebuffer[idx] == ' ');

            // skip end of line sequence
            rb.ridx += 2;

            return linebuffer;
        }
    }

    return NULL;
}

const char* serial_read_line()
{
    // read data from serial to local ringbuffer.
    // There is a change that too long lines will wrap the ringbuffer and
    // overwrite yet unread data.
    while (Serial.available()) {
        byte c = Serial.read();
        recvRingBuffer[recvRingBuffer.widx++] = c;
    }

    return parse_line(recvRingBuffer);
}

int serial_read(char* buffer, int count)
{
    int n = 0;
    while (serial_available(recvRingBuffer) > 0 && count-- > 0) {
        *buffer++ = recvRingBuffer[recvRingBuffer.ridx++];
        n++;
    }
    while (count-- > 0 && Serial.available()) {
        *buffer++ = Serial.read();
        n++;
    }
    return n;
}

void serial_write_line(const char* msg) { Serial.println(msg); }

void serial_write_char(char c) { Serial.write(c); }

void serial_echo_loop()
{
    while (true) {
        const char* cmd = serial_read_line();
        if (cmd) {
            serial_write_line(cmd);
        }
    }
}
