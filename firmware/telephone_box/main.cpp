#include <Arduino.h>

#include "main.hpp"
#include "serial_cmd.hpp"
#include "printf.h"
#include "timer.hpp"

#define wait_ms(ms) delay(ms)

// Telephone Box driver
// ========================================
// Developed on Arduino Nano

// States
enum LineState {
    LINE_STATE_UNKNOWN = 0,
    LINE_STATE_OFF_HOOK,
    LINE_STATE_ON_HOOK,  // same as line is open, no DC path.
    LINE_STATE_SHORT     // happens during dialing
};

enum State {
    STATE_NONE = 0,
    STATE_INITIAL,     // initializing
    STATE_IDLE,        // Nothing is happening. Phone is on-hook
    STATE_RING,        // Ringing the phone
    STATE_WAIT,        // Phone is off-hook, wait for user to start dialing the number.
    STATE_DIAL,        // Dial started, wait for a number
    STATE_DIAL2,       // Dial started, wait and receive full number
    STATE_DIAL_ERROR,  // dial fail, cleared by putting phone on-hook
    STATE_TERMINAL     // Debug and testing mode
};

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
static LineState sLineState = LINE_STATE_UNKNOWN;
static State sState = STATE_INITIAL;
static State sLastState = STATE_NONE;

// Voltage thresholds for line sense pin
#define LSENSE_ONHOOK_V 0.07  // line sense should be around 50-200mV depending of the phone
#define LSENSE_OFFHOOK_V 1.2

#define DIAL_MODE_NONE 0
#define DIAL_MODE_SINGLE 1
#define DIAL_MODE_FULL 2

static struct Configuration {
    int dialMode = DIAL_MODE_SINGLE;
    float onHookThreshold = LSENSE_ONHOOK_V;
    float offHookThreshold = LSENSE_OFFHOOK_V;
    int ringFreq = RING_FREQ_HZ;
} config;

void _putchar(char character) { serial_write_char(character); }

#define serial_printf(format, ...) printf(format SER_EOL, ##__VA_ARGS__)
#define serial_print(str) serial_write_line(str)

#define test_button() (digitalRead(TEST_BUTTON_PIN) == LOW)

static const char* stateToStr()
{
    const char* stateMap[] = {"-", "INIT", "IDLE", "RING", "WAIT", "DIAL", "DIAL2", "DIAL_ERROR", "TERMINAL"};

    return stateMap[sState];
}

bool setState(State newState)
{
    sLastState = sState;
    sState = newState;

    if (sLastState != sState) {
        serial_printf("STATE %s", stateToStr());
    }
}

bool setLineState(LineState newState)
{
    LineState oldState = sLineState;
    sLineState = newState;

    digitalWrite(LED_YELLOW_PIN, sLineState == LINE_STATE_OFF_HOOK);

    return oldState != sLineState;
}

static bool runSelfTest();

void setup()
{
    pinMode(LED_RED_PIN, OUTPUT);
    pinMode(LED_YELLOW_PIN, OUTPUT);
    digitalWrite(LED_RED_PIN, HIGH);
    digitalWrite(LED_YELLOW_PIN, HIGH);
    delay(500);
    digitalWrite(LED_RED_PIN, LOW);
    digitalWrite(LED_YELLOW_PIN, LOW);

    Serial.begin(57600);

    pinMode(TEST_BUTTON_PIN, INPUT_PULLUP);

    pinMode(PPA_PIN, OUTPUT);
    pinMode(PPB_PIN, OUTPUT);
    pinMode(RELAY_EN_PIN, OUTPUT);
    pinMode(POWER_DIS_PIN, OUTPUT);

    digitalWrite(PPA_PIN, LOW);
    digitalWrite(PPB_PIN, LOW);
    digitalWrite(RELAY_EN_PIN, LOW);
    digitalWrite(POWER_DIS_PIN, HIGH);


    pinMode(LINESENSE_PIN, INPUT);
    analogReference(DEFAULT);   // 5V
    analogRead(LINESENSE_PIN);  // First analog read must be discarded
    pinMode(TRIPSENSE_PIN, INPUT);

    if (!runSelfTest()) {
        // Indicate problem by blinking leds
        serial_print("WARN:-1");
        for (int i = 0; i < 10; i++) {
            digitalWrite(LED_RED_PIN, !digitalRead(LED_RED_PIN));
            delay(200);
        }
    }
}

bool isRingTrip() { return digitalRead(TRIPSENSE_PIN) == HIGH; }

static float sLineSenseVoltage;  // for debugging
LineState readLineState()
{
    const float vref = 5.0f;
    const int amax = (1 << 10) - 1;

    int lsense = analogRead(LINESENSE_PIN);
    float v = (vref * lsense) / amax;
    sLineSenseVoltage = v;
    if (v <= config.onHookThreshold) return LINE_STATE_ON_HOOK;
    if (v <= config.offHookThreshold) return LINE_STATE_OFF_HOOK;
    return LINE_STATE_SHORT;
}

bool updateLineState()
{
    LineState state = readLineState();
    return setLineState(state);
}

// Test assumes that phone is on-hook
static bool runSelfTest()
{
    bool pass = true;

    delay(100);

    serial_printf("INFO Telephone box %s", VERSION);
    serial_printf("INFO Test Button: %d", test_button());

    digitalWrite(RELAY_EN_PIN, HIGH);
    delay(RELAY_DELAY_MS);

    LineState lineState = readLineState();
    serial_printf("INFO Line state: %s", lineStateToStr(lineState));

    bool lineSenseCheck = (lineState == LINE_STATE_ON_HOOK);
    serial_printf("TEST Line sense: %s", lineSenseCheck ? "PASS" : "FAULT");
    pass = pass && lineSenseCheck;

    digitalWrite(RELAY_EN_PIN, LOW);
    delay(RELAY_DELAY_MS);

    bool tripCheck = !isRingTrip();
    serial_printf("TEST Ring-trip: %s", tripCheck ? "PASS" : "FAIL");

    pass = pass && tripCheck;

    return pass;
}

const char* serial_read_cmd()
{
    const char* cmd = serial_read_line();
    if (cmd) {
        if (!strlen(cmd)) {
            serial_print("READY");
            return NULL;
        } else if (!strcmp(cmd, "STATE")) {
            serial_print("OK");
            serial_printf("STATE %s", stateToStr());
            serial_print("READY");
            return NULL;
        } else if (!strcmp(cmd, "LINE")) {
            serial_print("OK");
            serial_printf("LINE %s", lineStateToStr(sLineState));
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

// Configuration keys
//
//  DM:<n>         int. 0 disable, 1: single digit dial (default), 2: number dial
//  TON:<voltage>  float. On-hook threshold voltage level
//  TOFF:<voltage> float. Off-hook threshold voltage level.
//  HZ:<freq>      int. Ringing frequency
//
bool parse_and_apply_config(const char* conf)
{
    if (*conf == '\0') {
        // print current configuration
        serial_printf("CONF DM:%d TON:%.2fV TOFF:%.2fV HZ:%d", config.dialMode, config.onHookThreshold, config.offHookThreshold, config.ringFreq);
    } else {
        while (*conf == ' ') {
            conf++;
            char* endptr = NULL;
            if (!strncmp(conf, "DM:", 3)) {  // Dial mode configuration
                conf += 3;
                int val = strtol(conf, &endptr, 10);
                if (*endptr != conf) {
                    config.dialMode = val;
                } else
                    return false;
            } else if (!strncmp(conf, "TON:", 4)) {  // On-hook threshold level
                conf += 3;
                float val = strtod(conf, &endptr);
                if (*endptr != conf) {
                    config.onHookThreshold = val;
                } else
                    return false;

            } else if (!strncmp(conf, "TOF:", 4)) {  // Off-hook threshold level
                conf += 3;
                float val = strtod(conf, &endptr);
                if (*endptr != conf) {
                    config.offHookThreshold = val;
                } else
                    return false;
            } else if (!strncmp(conf, "HZ:", 3)) {  // Ringing frequency
                conf += 3;
                int val = strtol(conf, &endptr, 10);
                if (*endptr != conf) {
                    config.ringFreq = val;
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

void handle_state_idle(StateStage stage)
{
    static Timer2 waitTimer(false, 100);
    uint32_t ts = millis();

    if (stage == ENTER) {
        digitalWrite(PPA_PIN, HIGH);  // required for ring-trip detection
        digitalWrite(PPB_PIN, LOW);
        digitalWrite(RELAY_EN_PIN, LOW);
        wait_ms(RELAY_DELAY_MS);  // let relay release
        serial_clear();
        serial_print("READY");
        waitTimer.reset(ts);
    }

    if (stage == EXECUTE) {
        bool ring_trip = isRingTrip();

        // Phone is off-hook
        if (ring_trip) {
            // Go the next state when line has been stable for a moment
            if (waitTimer.update(ts)) {
                serial_print("LINE OFF_HOOK");
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
            } else if (!strncmp(cmd, "CONF", 4)) {
                if (parse_and_apply_config(cmd + 4)) {
                    serial_print("OK");
                } else {
                    serial_print("INVALID");
                }
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
    static bool ringState = false;

    static Timer2 ringingTimeout(false, 30000);
    static Timer2 ringTime(false, RING_CADENCE_ON_MS);
    static Timer2 ringPauseTime(false, RING_CADENCE_OFF_MS);
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
        ringTime.reset(ts);
        ringPauseTime.reset(ts);
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
    if (stage == ENTER) {
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
            // dial begins
            switch (config.dialMode) {
                case DIAL_MODE_SINGLE: setState(STATE_DIAL); break;
                case DIAL_MODE_FULL: setState(STATE_DIAL2); break;
                case DIAL_MODE_NONE:  // ignore
                default: break;
            }
            return;
        }
    }
}

// Processes and reports a single digit at a time and returns back to the WAIT stage
void handle_state_dial(StateStage stage)
{
    enum DialState { PREPARE, PULSES, DONE };
    static DialState state = PREPARE;

    static Timer2 pulseTimeout(false, 2000);  // timeout for pulses to begin

    uint32_t ts = millis();

    if (stage == ENTER) {
        pulseTimeout.reset(ts);
        state = PREPARE;
        serial_print("DIAL_BEGIN");
    }

    if (stage == EXECUTE) {
        // discard commands
        discardCommands();
        updateLineState();

        switch (state) {
            case PREPARE:
                // line is in short, wait until it drops to on-hook
                if (pulseTimeout.update(ts)) {
                    // something is wrong, abort
                    setState(STATE_DIAL_ERROR);
                    state = DONE;
                } else if (sLineState == LINE_STATE_ON_HOOK) {
                    // Number pulses begin
                    state = PULSES;
                }
                break;
            case PULSES: {
                // NOTE! Code can spend in this loop up to a few seconds

                // Digit pulses have started, count them.
                bool pulseDetected = false;
                int dialPulses = 0;
                Timer2 numberTimeout(false, 200);  // timeout for individual digit
                while (!numberTimeout.update()) {
                    if (sLineState == LINE_STATE_ON_HOOK && !pulseDetected) {
                        dialPulses++;
                        pulseDetected = true;
                        numberTimeout.reset();
                    }
                    if (sLineState == LINE_STATE_OFF_HOOK && pulseDetected) {
                        pulseDetected = false;
                    }
                    updateLineState();
                }

                if (dialPulses > 0 && dialPulses <= 10) {
                    // print out dialed number
                    if (dialPulses == 10) dialPulses = 0;
                    serial_printf("DIAL %d", dialPulses);
                    setState(STATE_WAIT);
                } else {
                    serial_print("DIAL_ERROR");
                    setState(STATE_DIAL_ERROR);
                }
                state = DONE;
            } break;
            case DONE:
            default: break;
        }
    }
    if (stage == LEAVE) {
    }
}

// Processes and reports the full dialed number before returning back to the WAIT stage
void handle_state_dial2(StateStage stage)
{
    enum DialState { WAIT, PREPARE, PULSES, DONE };
    static DialState state = PREPARE;

    static Timer2 dialTimeout(false, 3500);   // timeout for the next digit
    static Timer2 pulseTimeout(false, 2000);  // timeout for the pulses to begin
    static char dialedNumber[16];
    const int maxDigits = sizeof(dialedNumber) - 1;
    static int digits = 0;

    uint32_t ts = millis();

    if (stage == ENTER) {
        digits = 0;
        dialTimeout.reset();
        pulseTimeout.reset(ts);
        state = PREPARE;
        serial_print("DIAL_BEGIN");
    }

    if (stage == EXECUTE) {
        // discard commands
        discardCommands();
        updateLineState();

        switch (state) {
            case WAIT:
                if (dialTimeout.update()) {
                    // timeout
                    state = DONE;
                }
                if (sLineState == LINE_STATE_ON_HOOK) {
                    // user has closed the phone
                    serial_print("LINE ON_HOOK");
                    digits = 0;
                    state = DONE;
                }
                if (sLineState == LINE_STATE_SHORT) {
                    // dial pulses are about to begin
                    pulseTimeout.reset();
                    state = PREPARE;
                }
                break;
            case PREPARE:
                // line is in short, wait until it drops to on-hook
                if (pulseTimeout.update(ts)) {
                    // something is wrong, abort
                    setState(STATE_DIAL_ERROR);
                    digits = -1;
                    state = DONE;
                } else if (sLineState == LINE_STATE_ON_HOOK) {
                    // Number pulses begin
                    state = PULSES;
                }
                break;
            case PULSES: {
                // NOTE! Code can spend in this loop up to a few seconds

                // Digit pulses have started, count them.
                bool pulseDetected = false;
                int dialPulses = 0;
                Timer2 numberTimeout(false, 200);  // timeout for an individual digit
                while (!numberTimeout.update()) {
                    if (sLineState == LINE_STATE_ON_HOOK && !pulseDetected) {
                        dialPulses++;
                        pulseDetected = true;
                        numberTimeout.reset();
                    }
                    if (sLineState == LINE_STATE_OFF_HOOK && pulseDetected) {
                        pulseDetected = false;
                    }
                    updateLineState();
                }

                if (dialPulses > 0 && dialPulses <= 10) {
                    // print out dialed number
                    if (dialPulses == 10) dialPulses = 0;
                    if (digits < maxDigits) {
                        dialedNumber[digits++] = '0' + dialPulses;
                    }
                    dialTimeout.reset();
                    state = WAIT;
                } else {
                    state = DONE;
                    digits = -1;
                }
                state = DONE;
            } break;
            case DONE:
                if (digits > 0) {
                    dialedNumber[digits] = '\0';
                    serial_printf("DIAL %s", dialedNumber);
                    setState(STATE_WAIT);
                } else if (digits == 0) {
                    serial_print("DIAL_CANCEL");
                    setState(STATE_WAIT);
                } else if (digits < 0) {
                    serial_print("DIAL_ERROR");
                    setState(STATE_DIAL_ERROR);
                }
            default: break;
        }
    }
    if (stage == LEAVE) {
    }
}

void handle_state_dialerror(StateStage stage)
{
    static Timer2 errorClearTimeout(false, 1000);
    static Timer2 blinkTimer(true, 200);
    uint32_t ts = millis();

    if (stage == ENTER) {
        errorClearTimeout.reset(ts);
        blinkTimer.reset(ts);
    }

    if (stage == EXECUTE) {
        if (blinkTimer.update(ts)) {
            digitalWrite(LED_RED_PIN, blinkTimer.flipflop());
        }

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
        if (sLineState == LINE_STATE_ON_HOOK) {
            if (errorClearTimeout.update(ts)) {
                // Reset back to idle state when line has been on hook for the required
                // time.
                serial_print("LINE ON_HOOK");
                setState(STATE_IDLE);
            }
        } else {
            errorClearTimeout.reset(ts);
        }
    }

    if (stage == LEAVE) {
        digitalWrite(LED_RED_PIN, LOW);
    }
}

void handle_state_terminal(StateStage stage)
{
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
                serial_printf("LINESTATE: %s (%.2fV)", lineStateToStr(sLineState), sLineSenseVoltage);
            }
            // Report linesense every second
            if (logTimer.update(ts)) {
                int a = analogRead(LINESENSE_PIN);
                float v = (5.0f * a) / ((1 << 10) - 1);
                serial_printf("LINESENSE: %u (%.2fV)", a, v);
            }
        }

        const struct {
            const char* name;
            uint8_t pin;
            uint8_t flags;
        } pinTable[] = {                                                                                     //
            {"BUTTON", TEST_BUTTON_PIN, 0}, {"RELAY_EN", RELAY_EN_PIN, 1}, {"POWER_DIS", POWER_DIS_PIN, 1},  //
            {"LED_YELLOW", LED_YELLOW_PIN, 1}, {"LED_RED", LED_RED_PIN, 1}};
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
                serial_printf("%s", buffer);
            }
            serial_print("EXIT");
            serial_print("HELP");

        } else if (!strcmp(cmd, "LINE")) {
            // Report line state
            updateLineState();
            serial_printf("LINESTATE: %s", lineStateToStr(sLineState));
            int a = analogRead(LINESENSE_PIN);
            float v = (5.0f * a) / ((1 << 10) - 1);
            serial_printf("LINESENSE: %u (%.2fV)", a, v);
            serial_printf("TRIPSENSE: %u", digitalRead(TRIPSENSE_PIN));
        } else if (!strncmp(cmd, "LINELOG ", 8)) {
            // Toggle line state logging
            linelog = !linelog;
            serial_printf("LINELOG: %d", linelog);
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
                    serial_printf("%s: %u", pinTable[i].name, digitalRead(pinTable[i].pin));
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
}

typedef void (*StateHandler)(StateStage);

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
const StateHandler stateHandlers[] = {
    handle_state_none,
    handle_state_initial,
    handle_state_idle,
    handle_state_ring,
    handle_state_wait,
    handle_state_dial,
    handle_state_dial2,
    handle_state_dialerror,
    handle_state_terminal
};
// clang-format on

void loop()
{
    if (sLastState != sState) {
        State prevState = sLastState;
        sLastState = sState;
        stateHandlers[prevState](LEAVE);
        stateHandlers[sState](ENTER);
    } else {
        stateHandlers[sState](EXECUTE);
    }
}
