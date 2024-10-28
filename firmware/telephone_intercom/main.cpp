#include <Arduino.h>

#include "main.hpp"
#include "serial_cmd.hpp"
#include "printf.h"
#include "timer.hpp"
#include "pwm_dac.hpp"

#define wait_ms(ms) delay(ms)

// Telephone Intercom driver
// ========================================
// Developed on Arduino Nano

// States
enum LineState {
    LINE_STATE_UNKNOWN = 0,
    LINE_STATE_OFF_HOOK,
    LINE_STATE_ON_HOOK,  // same as line is open, no DC path.
    // LINE_STATE_SHORT     // happens during dialing
};

enum State {
    STATE_NONE = 0,
    STATE_INITIAL,  // initializing
    STATE_IDLE,     // Nothing is happening. Phone is on-hook
    STATE_RING,     // Ringing the phone
    STATE_WAIT,     // Phone is off-hook
    STATE_CALL,     // Call active
    STATE_TERMINAL  // Debug and testing mode
};

int relayPins[2] = {RELAY1_EN_PIN, RELAY2_EN_PIN};
int lineSensePins[2] = {LINESENSE1_PIN, LINESENSE2_PIN};

static LineState sLineStates[2] = {LINE_STATE_UNKNOWN, LINE_STATE_UNKNOWN};

static const char* lineStateToStr(LineState state)
{
    const char* lineStateMap[] = {
        "-",
        "OFF_HOOK",
        "ON_HOOK",
        "SHORT",
    };

    return lineStateMap[state];
}

enum StateStage { ENTER, EXECUTE, LEAVE };

// Ringing parameters
#define RING_FREQ_HZ 25
#define RING_CADENCE_ON_MS 2000
#define RING_CADENCE_OFF_MS 2000

#if 0
static struct Configuration {
    int dialMode = DIAL_MODE_SINGLE;
    float onHookThreshold = LSENSE_ONHOOK_V;
    float offHookThreshold = LSENSE_OFFHOOK_V;
    int ringFreq = RING_FREQ_HZ;
    int ringCadenceOn = RING_CADENCE_ON_MS;
    int ringCadenceOff = RING_CADENCE_OFF_MS;
} config;
#endif

void _putchar(char character) { serial_write_char(character); }

#define serial_printfln(format, ...) printf(format SER_EOL, ##__VA_ARGS__)
#define serial_print(str) serial_write_line(str)

#define test_button() (digitalRead(SW1_PIN) == LOW || digitalRead(SW2_PIN) == LOW)

static const char* stateToStr();
void setState(State newState);


bool setLineState(int line, LineState newState)
{
    LineState oldState = sLineStates[line];
    sLineStates[line] = newState;
    return oldState != sLineStates[line];
}

// static bool runSelfTest();

void setup()
{
    pinMode(LED_RED_PIN, OUTPUT);

    digitalWrite(LED_RED_PIN, HIGH);
    delay(500);
    digitalWrite(LED_RED_PIN, LOW);

    Serial.begin(57600);

    pinMode(SW1_PIN, INPUT);
    pinMode(SW2_PIN, INPUT);

    pinMode(PPA_PIN, OUTPUT);
    pinMode(PPB_PIN, OUTPUT);
    digitalWrite(PPA_PIN, LOW);
    digitalWrite(PPB_PIN, LOW);

    for (int i = 0; i < 2; i++) {
        pinMode(relayPins[i], OUTPUT);
        digitalWrite(relayPins[i], LOW);
    }

    pinMode(POWER_DIS_PIN, OUTPUT);
    digitalWrite(POWER_DIS_PIN, HIGH);

    pinMode(TONE_DAC_PIN, OUTPUT);
    digitalWrite(TONE_DAC_PIN, HIGH);

    for (int i = 0; i < 2; i++) digitalWrite(relayPins[i], LOW);

    pinMode(TRIPSENSE_PIN, INPUT);

    analogReference(DEFAULT);    // 5V

    for (int i = 0; i < 2; i++)  // First analog read must be discarded
        analogRead(lineSensePins[i]);

    // Test relays
    for (int i = 0; i < 2; i++) {
        digitalWrite(relayPins[i], HIGH);
        delay(500);
        digitalWrite(relayPins[i], LOW);
    }

    serial_printfln("INFO Telephone Intercom %s %s", VERSION, __DATE__);

#if 0
    if (!runSelfTest()) {
        // Indicate problem by blinking leds
        serial_print("WARN:-1");
        for (int i = 0; i < 10; i++) {
            digitalWrite(LED_RED_PIN, !digitalRead(LED_RED_PIN));
            delay(200);
        }
    }
#endif

    pwm_dac_init();
}


bool isRingTrip() { return digitalRead(TRIPSENSE_PIN) == HIGH; }

static float sLineSenseVoltages[2];  // for debugging
LineState readLineState(int line)
{
    const float vref = 5.0f;
    const int amax = (1 << 10) - 1;

    int lsense = analogRead(lineSensePins[line]);
    float v = (vref * lsense) / amax;
    sLineSenseVoltages[line] = v;
    if (v <= LINESENSE_OFFHOOK_V) return LINE_STATE_ON_HOOK;
    return LINE_STATE_OFF_HOOK;
}

bool updateLineStates()
{
    bool changed = false;
    for (int line = 0; line < 2; line++) {
        LineState state = readLineState(line);
        changed = setLineState(line, state) || changed;
    }
    return changed;
}

#if 0

// Test assumes that phone is on-hook
static bool runSelfTest()
{
    bool pass = true;

    delay(100);

    serial_printfln("INFO Telephone box %s", VERSION);
    serial_printfln("INFO Test Button: %d", test_button());

    digitalWrite(RELAY_EN_PIN, HIGH);
    delay(RELAY_DELAY_MS);

    LineState lineState = readLineState();
    serial_printfln("INFO Line state: %s", lineStateToStr(lineState));

    bool lineSenseCheck = (lineState == LINE_STATE_ON_HOOK);
    serial_printfln("TEST Line sense: %s", lineSenseCheck ? "PASS" : "FAULT");
    pass = pass && lineSenseCheck;

    digitalWrite(RELAY_EN_PIN, LOW);
    delay(RELAY_DELAY_MS);

    bool tripCheck = !isRingTrip();
    serial_printfln("TEST Ring-trip: %s", tripCheck ? "PASS" : "FAIL");

    pass = pass && tripCheck;

    return pass;
}
#endif

const char* serial_read_cmd()
{
    const char* cmd = serial_read_line();
    if (cmd) {
        // serial_printfln("LINE:%s", cmd);
        if (!strlen(cmd)) {
            serial_print("READY");
            return NULL;
        } else if (!strcmp(cmd, "STATE")) {
            serial_print("OK");
            serial_printfln("STATE %s", stateToStr());
            serial_print("READY");
            return NULL;
        } else if (!strcmp(cmd, "LINE")) {
            serial_print("OK");
            for (int line = 0; line < 2; line++) {
                serial_printfln("LINE%d %s", (line + 1), lineStateToStr(sLineStates[line]));
            }

            serial_print("READY");
            return NULL;
        }
    }
    return cmd;
}

void handle_state_initial(StateStage stage)
{
    if (stage == ENTER) {
        setState(STATE_IDLE);
        delay(100);  // let things stabilize
    }
}

#if 0

// parses string like KEY:val
bool parse_key(const char* key, const char** conf)
{
    int len = strlen(key);
    if (!strncmp(key, *conf, len) && (*conf)[len] == ':') {
        *conf += len + 1;
        return true;
    }

    return false;
}

// Configuration keys
//
//  DM:<n>         int. 0 disable, 1: single digit dial (default)
//  TON:<voltage>  float. On-hook threshold voltage level
//  TOFF:<voltage> float. Off-hook threshold voltage level.
//  HZ:<freq>      int. Ringing frequency
//  RCON:<ms>      int. Ring cadence on
//  RCOFF:<ms>     int. Ring cadence off
//
bool parse_and_apply_config(const char* conf)
{
    if (*conf == '\0') {
        // print current configuration
        serial_printfln("CONF DM:%d", config.dialMode);
        serial_printfln("CONF TON:%.2fV", config.onHookThreshold);
        serial_printfln("CONF TOFF:%.2fV", config.offHookThreshold);
        serial_printfln("CONF HZ:%d", config.ringFreq);
        serial_printfln("CONF RCON:%d", config.ringCadenceOn);
        serial_printfln("CONF RCOFF:%d", config.ringCadenceOff);
    } else {
        while (*conf == ' ') {
            // serial_printfln("\"\r%s\"", conf);
            conf++;
            char* endptr = NULL;
            if (parse_key("DM", &conf)) {  // Dial mode configuration
                int val = strtol(conf, &endptr, 10);
                if (endptr != conf) {
                    config.dialMode = val;
                } else
                    return false;
            } else if (parse_key("TON", &conf)) {  // On-hook threshold level
                float val = strtod(conf, &endptr);
                if (endptr != conf) {
                    config.onHookThreshold = val;
                } else
                    return false;
            } else if (parse_key("TOFF", &conf)) {  // Off-hook threshold level
                float val = strtod(conf, &endptr);
                if (endptr != conf) {
                    config.offHookThreshold = val;
                } else
                    return false;
            } else if (parse_key("HZ", &conf)) {  // Ringing frequency
                int val = strtol(conf, &endptr, 10);
                if (endptr != conf) {
                    config.ringFreq = val;
                } else
                    return false;
            } else if (parse_key("RCON", &conf)) {  // Ring cadence off time
                float val = strtod(conf, &endptr);
                if (endptr != conf) {
                    config.ringCadenceOn = val;
                } else
                    return false;
            } else if (parse_key("RCOFF", &conf)) {  // Ring cadence off time
                float val = strtod(conf, &endptr);
                if (endptr != conf) {
                    config.ringCadenceOff = val;
                } else
                    return false;
            } else {
                return false;
            }
            conf = endptr;
        }
        if (*conf != '\0') return false;
    }
    return true;
}
#endif

void handle_state_idle(StateStage stage)
{
    static Timer2 waitTimer(false, 100);
    uint32_t ts = millis();

    if (stage == ENTER) {
        for (int line = 0; line < 2; line++) {
            digitalWrite(relayPins[line], LOW);
        }
        wait_ms(RELAY_DELAY_MS);  // let relays release
        serial_clear();
        serial_print("READY");
        waitTimer.reset(ts);
    }

    if (stage == EXECUTE) {
        bool changed = updateLineStates();

        if (!changed && (sLineStates[0] == LINE_STATE_OFF_HOOK || sLineStates[1] == LINE_STATE_OFF_HOOK)) {
            // Go the next state when line has been stable for a moment
            if (waitTimer.update(ts)) {
                for (int line = 0; line < 2; line++) {
                    serial_printfln("LINE %s", lineStateToStr(sLineStates[line]));
                }
                setState(STATE_WAIT);
                return;
            }
        } else {
            waitTimer.reset(ts);
        }
        // Check test button press
        if (test_button()) {
            delay(50);
            // wait until user releases button
            while (test_button())
                ;
            delay(10);  // let button stabilize
            setState(STATE_RING);
            return;
        }

        // Read commands and execute
        if (const char* cmd = serial_read_cmd()) {
            if (!strcmp(cmd, "RING")) {
                serial_print("OK");
                setState(STATE_RING);
                return;
            } else if (!strcmp(cmd, "TERMINAL")) {
                setState(STATE_TERMINAL);
                return;
                /*
                } else if (!strncmp(cmd, "CONF", 4)) {
                    if (parse_and_apply_config(cmd + 4)) {
                        serial_print("OK");
                    } else {
                        serial_print("INVALID");
                    }
                    */
            } else {
                serial_print("INVALID");
            }
            serial_print("READY");
        }
    }

    if (stage == LEAVE) {
    }
}

void handle_state_ring(StateStage stage)
{
#if 0
    static bool ringState = false;

    static Timer2 ringingTimeout(false, 30000);
    static Timer2 ringTime(false, config.ringCadenceOn);
    static Timer2 ringPauseTime(false, config.ringCadenceOff);
    static Timer2 ringHzTimer(true, 1000 / config.ringFreq / 2);
    static Timer2 ringTripStabilizationTimer(false, RING_TRIP_STABILIZATION_DELAY_MS);

    uint32_t ts = millis();

    if (stage == ENTER) {
        if (isRingTrip()) {
            setState(STATE_IDLE);
            return;
        }
        digitalWrite(LED_RED_PIN, HIGH);
        digitalWrite(PPB_PIN, HIGH);
        digitalWrite(PPA_PIN, LOW);
        digitalWrite(POWER_DIS_PIN, LOW);  // enable power for ring ac
        delay(500);

        ts = millis();
        ringingTimeout.reset(ts);
        ringTime.set(config.ringCadenceOn);
        ringPauseTime.set(config.ringCadenceOff);
        ringHzTimer.set(1000 / config.ringFreq / 2);
        ringTripStabilizationTimer.reset(ts);

        serial_print("READY");

        ringState = true;
        serial_print("RING");
        return;
    }

    if (stage == EXECUTE) {
        // Check test button press
        if (test_button()) {
            delay(50);
            // wait until user releases button
            while (test_button())
                ;
            delay(10);  // let button stabilize
            setState(STATE_IDLE);
            return;
        }

        if (ringTripStabilizationTimer.update(ts)) {
            bool ring_trip = isRingTrip();

            if (ring_trip) {
                // phone has been picked up
                serial_print("RING_TRIP");
                serial_print("LINE OFF_HOOK");
                setState(STATE_WAIT);
                return;
            }
        }

        // Read commands and execute
        if (const char* cmd = serial_read_cmd()) {
            if (!strcmp(cmd, "STOP")) {
                serial_print("OK");
                setState(STATE_IDLE);
                return;
            } else if (!strcmp(cmd, "RING")) {
                serial_print("OK");
            } else {
                serial_print("INVALID");
            }
            serial_print("READY");
        }

        if (ringingTimeout.update(ts)) {
            serial_print("RING_TIMEOUT");
            setState(STATE_IDLE);
            return;
        }

        if (ringState) {
            // phone is ringing
            if (ringTime.update(ts)) {
                // ring cycle expired, go to wait time
                digitalWrite(PPA_PIN, HIGH);
                digitalWrite(PPB_PIN, LOW);
                digitalWrite(LED_RED_PIN, HIGH);
                ringState = 0;
                serial_print("RING_PAUSE");
                ringPauseTime.reset(ts);
            } else {
                // ring cycle active
                if (ringHzTimer.update(ts)) {
                    digitalWrite(PPA_PIN, !ringHzTimer.flipflop());
                    digitalWrite(PPB_PIN, ringHzTimer.flipflop());
                    digitalWrite(LED_RED_PIN, ringHzTimer.flipflop());
                }
            }
        } else if (ringPauseTime.update(ts)) {
            ringState = true;
            serial_print("RING");
            ringTime.reset(ts);
            ringHzTimer.reset();
        }
        return;
    }

    if (stage == LEAVE) {
        digitalWrite(LED_RED_PIN, LOW);
        digitalWrite(PPB_PIN, LOW);
        digitalWrite(PPA_PIN, LOW);
        digitalWrite(POWER_DIS_PIN, HIGH);
        return;
    }
#endif
}

// Called to read and discard commands when they can not be executed
void discardCommands()
{
    while (serial_read_cmd()) {
        serial_print("INVALID");
        serial_print("READY");
    }
}

void handle_state_wait(StateStage stage)
{
#if 0
    if (stage == ENTER) {
        digitalWrite(PPA_PIN, HIGH);  // required for ring-trip detection
        digitalWrite(PPB_PIN, LOW);
        
        digitalWrite(RELAY_EN_PIN, HIGH);
        wait_ms(RELAY_DELAY_MS);  // let relay latch
    }

    if (stage == EXECUTE) {
        if (const char* cmd = serial_read_cmd()) {
            if (!strcmp(cmd, "TERMINAL")) {
                setState(STATE_TERMINAL);
                return;
            } else {
                serial_print("INVALID");
            }
            serial_print("READY");
        }

        updateLineState();

        // Wait for the number dial in
        if (sLineState == LINE_STATE_ON_HOOK) {
            serial_print("LINE ON_HOOK");
            setState(STATE_IDLE);
            return;
        } else if (sLineState == LINE_STATE_SHORT) {
            // Rotary dial shorts the line when user starts winding the dial to the number

            // Wait for a while to filter out sporadic shorts. These
            // maybe triggered by users finger slipping of the rotary dial, DTMF and transistor
            // phones current demand peaks etc.
            Timer2 shortTimer(false, 150);
            while (sLineState == LINE_STATE_SHORT) {
                uint32_t ts = millis();
                if (shortTimer.update(ts)) {
                    // Line has been shorted for long enough. Dial begins
                    switch (config.dialMode) {
                        case DIAL_MODE_SINGLE: setState(STATE_DIAL); break;
                        case DIAL_MODE_NONE:  // ignore
                        default: break;
                    }
                    return;
                }
                updateLineState();
            }
        }
    }
#endif
}

void handle_state_call(StateStage stage) {}

void handle_state_terminal(StateStage stage)
{
#if 0
    static Timer2 logTimer(true, 1000);
    static bool linelog = false;

    uint32_t ts = millis();

    if (stage == ENTER) {
        // digitalWrite(LED_GREEN, HIGH);
        digitalWrite(LED_YELLOW_PIN, HIGH);
        digitalWrite(LED_RED_PIN, HIGH);
        serial_print("Testing terminal");
        serial_print(">");
        linelog = false;
        logTimer.reset(ts);
    }
    if (stage == EXECUTE) {
        if (linelog) {
            // Log line state every time it changes
            if (updateLineState()) {
                serial_printfln("LINESTATE: %s (%.2fV)", lineStateToStr(sLineState), sLineSenseVoltage);
            }
            // Report linesense every second
            if (logTimer.update(ts)) {
                int a = analogRead(LINESENSE_PIN);
                float v = (5.0f * a) / ((1 << 10) - 1);
                serial_printfln("LINESENSE: %u (%.2fV)", a, v);
            }
        }

        const struct {
            const char* name;
            uint8_t pin;
            uint8_t flags;
        } pinTable[] = {                                                                                     //
            {"BUTTON", TEST_BUTTON_PIN, 0},  //
            {"SW1", SW1_PIN, 0}, //
            {"SW2", SW2_PIN, 0}, //
            {"RELAY1_EN", RELAY1_EN_PIN, 1}, //
            {"RELAY2_EN", RELAY2_EN_PIN, 1}, //
            {"POWER_DIS", POWER_DIS_PIN, 1},  //
            {"LED_RED", LED_RED_PIN, 1} };
        const int pinCount = sizeof(pinTable) / sizeof(pinTable[0]);

        const char* cmd = serial_read_line();
        if (!cmd) return;

        if (!strcmp(cmd, "HELP")) {
            serial_print("LINE");
            serial_print("LINELOG [1|0]");
            serial_print("RING");
            for (int i = 0; i < pinCount; i++) {
                char buffer[32];
                if (pinTable[i].flags) {
                    snprintf(buffer, 32, "%s [1|0]", pinTable[i].name);
                } else {
                    strcpy(buffer, pinTable[i].name);
                }
                serial_printfln("%s", buffer);
            }
            serial_print("EXIT");
            serial_print("HELP");

        } else if (!strcmp(cmd, "LINE")) {
            // Report line state
            updateLineState();
            serial_printfln("LINESTATE: %s", lineStateToStr(sLineState));
            int a = analogRead(LINESENSE_PIN);
            float v = (5.0f * a) / ((1 << 10) - 1);
            serial_printfln("LINESENSE: %u (%.2fV)", a, v);
            serial_printfln("TRIPSENSE: %u", digitalRead(TRIPSENSE_PIN));
        } else if (!strncmp(cmd, "LINELOG ", 8)) {
            // Toggle line state logging
            linelog = !linelog;
            serial_printfln("LINELOG: %d", linelog);
        } else if (!strcmp(cmd, "RING")) {
            setState(STATE_RING);
            return;
        } else if (!strcmp(cmd, "EXIT")) {
            setState(STATE_WAIT);
            return;
        } else {
            for (int i = 0; i < pinCount; i++) {
                if (!strncmp(cmd, pinTable[i].name, strlen(pinTable[i].name))) {
                    cmd += strlen(pinTable[i].name);
                    if (*cmd && pinTable[i].flags) {
                        digitalWrite(pinTable[i].pin, atoi(cmd));
                    }
                    serial_printfln("%s: %u", pinTable[i].name, digitalRead(pinTable[i].pin));
                    break;
                }
            }
        }
        serial_print(">");
    }
    if (stage == LEAVE) {
        digitalWrite(LED_YELLOW_PIN, LOW);
        digitalWrite(LED_RED_PIN, LOW);
        digitalWrite(RELAY_EN_PIN, LOW);
        digitalWrite(POWER_DIS_PIN, HIGH);
        digitalWrite(RELAY_EN_PIN, LOW);
    }
#endif
}


typedef void (*StateHandler)(StateStage);

static State sState = STATE_INITIAL;
static State sLastState = STATE_NONE;

void setState(State newState)
{
    sLastState = sState;
    sState = newState;
}

void handle_state_none(StateStage stage)
{
    // dummy handler
    if (stage == ENTER) {
        // do nothing
    }
    if (stage == EXECUTE) {
        // do nothing
    }
    if (stage == LEAVE) {
        // do nothing
    }
}

// clang-format off
static struct {
    StateHandler handler;
    const char* name;
} sStateTbl[] = {
    { handle_state_none, "-" },
    { handle_state_initial, "INIT"},
    { handle_state_idle, "IDLE"},
    { handle_state_ring, "RING"},
    { handle_state_wait, "WAIT"},
    { handle_state_call, "CALL"},
    { handle_state_terminal, "TERMINAL"}
};
// clang-format on

static const char* stateToStr() { return sStateTbl[sState].name; }

void loop()
{
    if (sLastState != sState) {
        State prevState = sLastState;
        sLastState = sState;
        sStateTbl[prevState].handler(LEAVE);
        serial_printfln("STATE %s", stateToStr());
        sStateTbl[sState].handler(ENTER);
    } else {
        sStateTbl[sState].handler(EXECUTE);
    }
}
