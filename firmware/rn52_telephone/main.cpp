#include <Arduino.h>
#include <util/atomic.h>
#include "printf.h"
#include "serial_reader.hpp"

/*
Serial interface: 115200-8-N-1

'D' command
*** Settings ***
BTA=000666553382
BTAC=NotConnected
BTName=KTV
Authen=4
COD=200404
DiscoveryMask=08
ConnectionMask=08
PinCode=1409
AudioConfig=0002
AudioRoute=ANALOG
CodecsEnabled=00
AudioCodec=Unknown
ExtFeatures=2004
*/

#if !defined(ARDUINO_AVR_NANO_EVERY)
#error "Nano Every required"
#endif

#define STATUS_PIN 2
#define CMD_MODE_PIN 3

/*
Headset Profile (HSP)
1. Set the bit ‘Audio’ in the Service Class field
Further, a device may optionally:
1. Indicate ‘Audio’ as Major Device class
2. Indicate “Headset” as the Minor Device class
*/
// Refer to Sect. 2.8 Class of Device, Bluetooth Assigned Numbers 2025-09-12

#define RN52_CLASS_OF_DEVICE 0x200404  // Audio, Wearable Headset Device, Headset

#define RN52_PIN_CODE "1409"
#define RN52_DEVICE_NAME "KTV"

#define RN52_DIAL "A"
#define RN52_END_CALL "E"
#define RN52_ACCEPT_CALL "C"
#define RN52_SET_CLASS "SC"
#define RN52_SET_NAME "SN"
#define RN52_SET_PIN "SP"
#define RN52_SET_DISCOVERY_MASK "SD"
#define RN52_SET_CONNECTION_MASK "SK"
#define RN52_SET_FACTORY "SF"
#define RN52_SET_AUTHENTICATION "SA"
#define RN52_SET_EXT_FEATURES "S%"
#define RN52_GET_STATUS "Q"
#define RN52_GET_SETTINGS "D"
#define RN52_GET_VERSION "V"

#define RN52_AUTHENTICATION_OPEN 0
#define RN52_AUTHENTICATION_SPP 1             // SPP keyboard mode
#define RN52_AUTHENTICATION_SPP_JUST_WORKS 2  // SPP keyboard mode
#define RN52_AUTHENTICATION_PIN 4             // PIN code

#define RN52_STATUS_ERR "ERR"
#define RN52_STATUS_OK "AOK"
#define RN52_STATUS_END "END"
#define RN52_STATUS_CMD "CMD"

// RN52 Connection States
#define RN52_CONN_STATE_LIMBO 0                 // Logically off, but physically on
#define RN52_CONN_STATE_CONNECTABLE 1           // The module is connectable, page scanning
#define RN52_CONN_STATE_DISCOVERABLE 2          // The module is connectable and discoverable
#define RN52_CONN_STATE_CONNECTED 3             // The module is connected to an audio gateway
#define RN52_CONN_STATE_OUTGOING_CALL 4         // Outgoing call established
#define RN52_CONN_STATE_INCOMING_CALL 5         // Incoming call established
#define RN52_CONN_STATE_ACTIVE_CALL 6           // Active call with audio in headset
#define RN52_CONN_STATE_TEST_MODE 7             // Test mode
#define RN52_CONN_STATE_THREE_WAY_WAITING 8     // Active call with second call waiting
#define RN52_CONN_STATE_THREE_WAY_HOLD 9        // Active call with second call on hold
#define RN52_CONN_STATE_THREE_WAY_MULTI 10      // Active call with second call on hold (multi)
#define RN52_CONN_STATE_INCOMING_HOLD 11        // Incoming call on hold
#define RN52_CONN_STATE_ACTIVE_CALL_HANDSET 12  // Active call with audio in handset
#define RN52_CONN_STATE_AUDIO_STREAMING 13      // A2DP audio streaming
#define RN52_CONN_STATE_LOW_BATTERY 14          // System low battery

#define RN52_EOL "\r\n"

#define RN52Serial Serial1

StreamLineReader rn52_reader(RN52Serial);
StreamLineReader serial_reader(Serial);

uint8_t rn52debugf = 0;

void rn52_write(const char* s)
{
    if (rn52debugf) printf("RN52<%s", s);
    RN52Serial.write(s);
}

void rn52_write(const char* s, int n)
{
    if (rn52debugf) printf("RN52<%*s", n, s);
    RN52Serial.write(s, n);
}

char* rn52_read_line()
{
    char* line = rn52_reader.read_line();
    if (line) {
        if (rn52debugf) printf("RN52>%s\r\n", line);
    }
    return line;
}

void _putchar(char c) { Serial.write(c); }

int rn52_wait_cmd_result()
{
    uint32_t ts = millis() + 1000;
    int status = -2;  // timeout
    while (ts > millis()) {
        const char* line = rn52_read_line();
        if (line) {
            if (!strcmp(line, RN52_STATUS_OK))
                status = 0;
            else if (!strcmp(line, RN52_STATUS_ERR))
                status = -1;
            else
                break;
        }
    }
    return status;
}

int rn52_cmd(const char* cmd)
{
    char cmd_buf[32];
    int n = snprintf(cmd_buf, sizeof(cmd_buf), "%s" RN52_EOL, cmd);
    rn52_write(cmd_buf, n);

    return rn52_wait_cmd_result();
}

int rn52_cmd_dec(const char* cmd, int value)
{
    char cmd_buf[32];
    int n = snprintf(cmd_buf, sizeof(cmd_buf), "%s,%d" RN52_EOL, cmd, value);
    rn52_write(cmd_buf, n);

    return rn52_wait_cmd_result();
}

int rn52_cmd_hex(const char* cmd, int width, uint32_t value)
{
    char cmd_buf[32];
    int n = snprintf(cmd_buf, sizeof(cmd_buf), "%s,%0*lX" RN52_EOL, cmd, 2 * width, value);
    rn52_write(cmd_buf, n);

    return rn52_wait_cmd_result();
}

int rn52_cmd_str(const char* cmd, const char* str, int len)
{
    char cmd_buf[32];
    int n = snprintf(cmd_buf, sizeof(cmd_buf), "%s,%*s" RN52_EOL, cmd, len, str);
    rn52_write(cmd_buf, n);

    return rn52_wait_cmd_result();
}

union RN52Status {
    struct {
        uint8_t conn_state : 4;
        uint8_t hfp_audio_volume_change : 1;
        uint8_t hftp_mic_volume_change : 1;
        uint8_t : 2;  // reserved

        uint8_t iap_active : 1;
        uint8_t spp_active : 1;
        uint8_t a2dp_active : 1;
        uint8_t hsp_active : 1;
        uint8_t caller_id_notify : 1;
        uint8_t track_change_notify : 1;
        uint8_t : 2;  // reserved

    } bits;
    uint16_t raw;
};

int rn52_get_status(uint16_t* status)
{
    int result = -2;
    rn52_write(RN52_GET_STATUS RN52_EOL);
    uint32_t ts = millis() + 1000;
    while (ts > millis()) {
        const char* line = rn52_read_line();
        if (line) {
            char* end;
            *status = strtol(line, &end, 16);
            if (end != line)
                result = 1;
            else
                result = -1;
            break;
        }
    }
    return result;
}

void dump_response()
{
    uint32_t ts = millis() + 1000;
    while (ts > millis()) {
        const char* line = rn52_read_line();
        if (line) {
            printf("%s\r\n", line);
        }
    }
}

int rn52_print_version()
{
    rn52_write(RN52_GET_VERSION RN52_EOL);
    dump_response();
    return 0;
}

int rn52_print_settings()
{
    rn52_write(RN52_GET_SETTINGS RN52_EOL);
    dump_response();
    return 0;
}

volatile uint8_t statusCounter = 1;

static void statusPinHandler() { statusCounter++; }

int rn52_wait_for(const char* str, int timeoutms = 1000)
{
    uint32_t ts = millis() + timeoutms;
    while (ts > millis()) {
        const char* line = rn52_read_line();
        if (line) {
            if (!strcmp(line, str)) return 0;
        }
    }
    return -1;
}

void rn52_configure()
{
    printf("Configuring RN52\r\n");

    rn52_write(RN52_GET_SETTINGS RN52_EOL);
    uint32_t ts = millis() + 1000;
    while (ts > millis()) {
        char* keyval = rn52_read_line();

        if (!keyval) continue;
        char* value = strchr(keyval, '=');
        if (!value) continue;
        *value++ = '\0';

        int err = 1;
        if (!strcmp(keyval, "Authen") && atoi(value) != RN52_AUTHENTICATION_PIN) {
            err = rn52_cmd_dec(RN52_SET_AUTHENTICATION, RN52_AUTHENTICATION_PIN);
        } else if (!strcmp(keyval, "PinCode") && strcmp(value, RN52_PIN_CODE) != 0) {
            err = rn52_cmd_str(RN52_SET_PIN, RN52_PIN_CODE, 4);
        } else if (!strcmp(keyval, "COD") && strtol(value, NULL, 16) != RN52_CLASS_OF_DEVICE) {
            err = rn52_cmd_hex(RN52_SET_CLASS, 3, RN52_CLASS_OF_DEVICE);
        } else if (!strcmp(keyval, "DiscoveryMask") && strtol(value, NULL, 16) != 0x08) {
            err = rn52_cmd_hex(RN52_SET_DISCOVERY_MASK, 1, 0x08);   // enable only headset profile
        } else if (!strcmp(keyval, "ConnectionMask") && strtol(value, NULL, 16) != 0x08) {
            err = rn52_cmd_hex(RN52_SET_CONNECTION_MASK, 1, 0x08);  // enable only headset profile
        } else if (!strcmp(keyval, "BTName") && strcmp(value, RN52_DEVICE_NAME) != 0) {
            err = rn52_cmd_str(RN52_SET_NAME, RN52_DEVICE_NAME, 3);
        }
        if (err != 1) {
            printf("%s=%s (%d)\r\n", keyval, value, err);
        }
    }
    printf("Configuration done\r\n");
}

RN52Status status;
void update_rn52_status()
{
    if (rn52_get_status(&status.raw) > 0) {
        // clang-format off
        printf("Status: 0x%04X ConnState=%d IAP=%d SPP=%d A2DP=%d HSP=%d\r\n",
            status,
            status.bits.conn_state,
            status.bits.iap_active,
            status.bits.spp_active,
            status.bits.a2dp_active,
            status.bits.hsp_active
        );
        // clang-format on
    } else {
        printf("Failed to get status\r\n");
    }
}

void setup()
{
    Serial.begin(115200);
    RN52Serial.begin(115200);

    digitalWrite(CMD_MODE_PIN, LOW);
    pinMode(CMD_MODE_PIN, OUTPUT);
    pinMode(STATUS_PIN, INPUT);

    attachInterrupt(digitalPinToInterrupt(STATUS_PIN), statusPinHandler, FALLING);

    printf("RN52 Telephone Interface " __DATE__ "\r\n");

    printf("Waiting command mode\r\n");
    while (true) {
        if (rn52_wait_for(RN52_STATUS_CMD) == 0) {
            printf("Command mode ready\r\n");
            break;
        }
        digitalWrite(CMD_MODE_PIN, HIGH);
        delay(500);
        digitalWrite(CMD_MODE_PIN, LOW);
    }

    rn52_print_version();
    rn52_print_settings();
    rn52_configure();

    rn52debugf = 1;
}

void passthrough()
{
#if 0
    if(Serial.available()) {
        RN52Serial.write((char)Serial.read());
    }
    if(RN52Serial.available()) {
        Serial.write((char)RN52Serial.read());
    }
#endif

#if 1
    // Passthrough loop
    const char* line = serial_reader.read_line();
    if (line) {
        RN52Serial.print(line);
        RN52Serial.print(RN52_EOL);
    }
    line = rn52_reader.read_line();
    if (line) {
        Serial.print(line);
        Serial.print(RN52_EOL);
    }
#endif
}

void loop()
{
    passthrough();

    if (statusCounter > 0) {
        int temp;
        ATOMIC_BLOCK(ATOMIC_FORCEON)
        {
            temp = statusCounter;
            statusCounter = 0;
        }

        // incoming call
        /*
        10. From CMD mode in the terminal emulator, enter the “Q” command to retrieve
        connection status. The second byte should indicate state “05” (incoming call).
        11. From CMD mode in the terminal emulator, enter the “C” command to accept the
        incoming call.
        12. From CMD mode in the terminal emulator, enterq the “Q” command to retrieve
        connection status. The second byte should indicate state “06” (active call).
        */
        printf("* Status changed %d\r\n", temp);

        update_rn52_status();
    }
}
