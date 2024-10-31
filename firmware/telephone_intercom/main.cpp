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

#define LINE_COUNT 2

int relayPins[LINE_COUNT] = {RELAY1_EN_PIN, RELAY2_EN_PIN};
int lineSensePins[LINE_COUNT] = {LINESENSE1_PIN, LINESENSE2_PIN};

static LineState sLineStates[LINE_COUNT] = {LINE_STATE_UNKNOWN, LINE_STATE_UNKNOWN};

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

void _putchar(char character) { serial_write_char(character); }

#define serial_printfln(format, ...) printf(format SER_EOL, ##__VA_ARGS__)
#define serial_println(str) serial_write_line(str)

#define test_button() (digitalRead(SW1_PIN) == LOW || digitalRead(SW2_PIN) == LOW)

static const char* stateToStr();
void setState(State newState);


bool setLineState(int line, LineState newState)
{
    LineState oldState = sLineStates[line];
    sLineStates[line] = newState;
    return oldState != sLineStates[line];
}

#define tone_is_enabled() pwm_dac_enabled()
#define tone_enable() pwm_dac_enable()
#define tone_disable() pwm_dac_disable()

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

    for (int i = 0; i < LINE_COUNT; i++) {
        pinMode(relayPins[i], OUTPUT);
        digitalWrite(relayPins[i], LOW);
    }

    pinMode(POWER_DIS_PIN, OUTPUT);
    digitalWrite(POWER_DIS_PIN, HIGH);

    pinMode(TONE_DAC_PIN, OUTPUT);
    digitalWrite(TONE_DAC_PIN, HIGH);

    for (int i = 0; i < LINE_COUNT; i++) digitalWrite(relayPins[i], LOW);

    pinMode(TRIPSENSE_PIN, INPUT);

    analogReference(DEFAULT);             // 5V

    for (int i = 0; i < LINE_COUNT; i++)  // First analog read must be discarded
        analogRead(lineSensePins[i]);

    // Test relays
    for (int i = 0; i < LINE_COUNT; i++) {
        digitalWrite(relayPins[i], HIGH);
        delay(500);
        digitalWrite(relayPins[i], LOW);
    }

    serial_printfln("INFO Telephone Intercom %s %s", VERSION, __DATE__);

#if 0
    if (!runSelfTest()) {
        // Indicate problem by blinking leds
        serial_println("WARN:-1");
        for (int i = 0; i < 10; i++) {
            digitalWrite(LED_RED_PIN, !digitalRead(LED_RED_PIN));
            delay(200);
        }
    }
#endif

    pwm_dac_init();
}


bool isRingTrip() { return digitalRead(TRIPSENSE_PIN) == HIGH; }

static float sLineSenseVoltages[LINE_COUNT];  // for debugging
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
    for (int line = 0; line < LINE_COUNT; line++) {
        LineState state = readLineState(line);
        changed = setLineState(line, state) || changed;
    }
    return changed;
}

int compareLineStates(LineState state)
{
    int c = 0;
    for (int line = 0; line < LINE_COUNT; line++) {
        if (sLineStates[line] == state) c++;
    }
    return c;
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
            serial_println("READY");
            return NULL;
        } else if (!strcmp(cmd, "STATE")) {
            serial_println("OK");
            serial_printfln("STATE %s", stateToStr());
            serial_println("READY");
            return NULL;
        } else if (!strcmp(cmd, "LINE")) {
            serial_println("OK");
            for (int line = 0; line < LINE_COUNT; line++) {
                serial_printfln("LINE%d %s", (line + 1), lineStateToStr(sLineStates[line]));
            }

            serial_println("READY");
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

void handle_state_idle(StateStage stage)
{
    static Timer2 waitTimer(false, 100);
    uint32_t ts = millis();

    if (stage == ENTER) {
        for (int line = 0; line < LINE_COUNT; line++) {
            digitalWrite(relayPins[line], LOW);
        }
        wait_ms(RELAY_DELAY_MS);  // let relays release
        serial_clear();
        serial_println("READY");
        waitTimer.reset(ts);
    }

    if (stage == EXECUTE) {
        bool changed = updateLineStates();

        if (!changed && compareLineStates(LINE_STATE_OFF_HOOK)) {
            // Go the next state when line has been stable for a moment and at least one line is off-hook
            if (waitTimer.update(ts)) {
                for (int line = 0; line < LINE_COUNT; line++) {
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
                serial_println("OK");
                setState(STATE_RING);
                return;
            } else if (!strcmp(cmd, "TERMINAL")) {
                setState(STATE_TERMINAL);
                return;
                /*
                } else if (!strncmp(cmd, "CONF", 4)) {
                    if (parse_and_apply_config(cmd + 4)) {
                        serial_println("OK");
                    } else {
                        serial_println("INVALID");
                    }
                    */
            } else {
                serial_println("INVALID");
            }
            serial_println("READY");
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
    static Timer2 ringHzTimer(true, 1000 / RING_FREQ_HZ / 2);
    static Timer2 ringTripStabilizationTimer(false, RING_TRIP_STABILIZATION_DELAY_MS);

    uint32_t ts = millis();

    if (stage == ENTER) {
        tone_disable();

        // Ensure that there is at least one line to ring
        updateLineStates();
        if (compareLineStates(LINE_STATE_OFF_HOOK) == LINE_COUNT) {
            setState(STATE_CALL);
            return;
        }
        if (compareLineStates(LINE_STATE_ON_HOOK) == LINE_COUNT) {
            setState(STATE_IDLE);
            return;
        }

        digitalWrite(PPB_PIN, LOW);
        digitalWrite(PPA_PIN, HIGH);

        // Enable ring circuit for on-hook lines
        for (int line = 0; line < LINE_COUNT; line++) {
            if (sLineStates[line] == LINE_STATE_ON_HOOK) {
                digitalWrite(relayPins[line], HIGH);
            }
        }

        wait_ms(RELAY_DELAY_MS);  // let relays to latch

        digitalWrite(LED_RED_PIN, HIGH);

        digitalWrite(PPA_PIN, LOW);
        digitalWrite(PPB_PIN, HIGH);
        digitalWrite(POWER_DIS_PIN, LOW);  // enable power for ring ac
        delay(500);

        ts = millis();
        ringingTimeout.reset(ts);
        ringTime.reset(ts);
        ringPauseTime.reset(ts);
        ringHzTimer.reset(ts);
        ringTripStabilizationTimer.reset(ts);

        serial_println("READY");

        ringState = true;
        serial_println("RING");
        return;
    }

    if (stage == EXECUTE) {
        if (ringTripStabilizationTimer.update(ts)) {
            bool ring_trip = isRingTrip();

            if (ring_trip) {
                // phone has been picked up
                serial_println("RING_TRIP");
                serial_println("LINE OFF_HOOK");
                setState(STATE_CALL);
                return;
            }
        }

        updateLineStates();
        if (compareLineStates(LINE_STATE_ON_HOOK) == LINE_COUNT) {
            setState(STATE_IDLE);
            return;
        }

        // Read commands and execute
        if (const char* cmd = serial_read_cmd()) {
            if (!strcmp(cmd, "STOP")) {
                serial_println("OK");
                setState(STATE_IDLE);
                return;
            } else if (!strcmp(cmd, "RING")) {
                serial_println("OK");
            } else {
                serial_println("INVALID");
            }
            serial_println("READY");
        }

        if (ringingTimeout.update(ts)) {
            serial_println("RING_TIMEOUT");
            setState(STATE_IDLE);
            return;
        }

        if (ringState) {
            // phone is ringing
            if (ringTime.update(ts)) {
                tone_disable();
                // ring cycle expired, go to wait time
                digitalWrite(PPA_PIN, HIGH);
                digitalWrite(PPB_PIN, LOW);
                digitalWrite(LED_RED_PIN, HIGH);
                ringState = false;
                serial_println("RING_PAUSE");
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
            tone_enable();
            ringState = true;
            serial_println("RING");
            ringTime.reset(ts);
            ringHzTimer.reset();
        }
        return;
    }

    if (stage == LEAVE) {
        tone_disable();
        digitalWrite(LED_RED_PIN, LOW);
        digitalWrite(PPB_PIN, LOW);
        digitalWrite(PPA_PIN, LOW);
        digitalWrite(POWER_DIS_PIN, HIGH);
        for (int line = 0; line < LINE_COUNT; line++) {
            digitalWrite(relayPins[line], LOW);
        }
        return;
    }
}

// Called to read and discard commands when they can not be executed
void discardCommands()
{
    while (serial_read_cmd()) {
        serial_println("INVALID");
        serial_println("READY");
    }
}

void handle_state_wait(StateStage stage)
{
    static Timer2 waitTimeout(true, 3000);
    uint32_t ts = millis();

    if (stage == ENTER) {
        waitTimeout.reset(ts);
        tone_enable();
    }

    if (stage == EXECUTE) {
        if (const char* cmd = serial_read_cmd()) {
            if (!strcmp(cmd, "TERMINAL")) {
                setState(STATE_TERMINAL);
                return;
            } else {
                serial_println("INVALID");
            }
            serial_println("READY");
        }

        updateLineStates();

        if (compareLineStates(LINE_STATE_OFF_HOOK) == LINE_COUNT) {
            setState(STATE_CALL);
        }

        if (waitTimeout.update(ts)) {
            // setState(STATE_RING);
        }
    }

    if (stage == LEAVE) {
        tone_disable();
    }
}

void handle_state_call(StateStage stage)
{
    static bool toneActive;
    static Timer2 toneTimer(true, 500);

    uint32_t ts = millis();

    if (stage == ENTER) {
        delay(200);  // wait for a while for things to stabilize
        toneTimer.reset(ts);
        toneActive = false;
    }
    if (stage == EXECUTE) {
        if (updateLineStates()) {
            if (compareLineStates(LINE_STATE_OFF_HOOK) == 1) {
                // only one line active.
                tone_enable();
                toneActive = true;
            } else if (compareLineStates(LINE_STATE_OFF_HOOK) == LINE_COUNT) {
                // back to a normal call
                tone_disable();
                toneActive = false;
            }
            toneTimer.reset(ts);
        }
        // Go back to idle state when all the lines have hanged up and are on-hook
        if (compareLineStates(LINE_STATE_ON_HOOK) == LINE_COUNT) {
            setState(STATE_IDLE);
        }
        if (toneActive && toneTimer.update(ts)) {
            if (toneTimer.flipflop()) {
                tone_enable();
            } else {
                tone_disable();
            }
        }
    }
    if (stage == LEAVE) {
        tone_disable();
    }
}

void handle_state_terminal(StateStage stage)
{
    static Timer2 logTimer(true, 1000);
    static bool linelog = false;

    uint32_t ts = millis();

    if (stage == ENTER) {
        // digitalWrite(LED_GREEN, HIGH);
        digitalWrite(LED_RED_PIN, HIGH);
        serial_println("Testing terminal");
        serial_println(">");
        linelog = false;
        logTimer.reset(ts);
    }
    if (stage == EXECUTE) {
        if (linelog) {
            // Log line state every time it changes
            if (updateLineStates()) {
                for (int line; line < LINE_COUNT; line++) {
                    serial_printfln("LINESTATE%d: %s (%.2fV)", (line + 1), lineStateToStr(sLineStates[line]), sLineSenseVoltages[line]);
                }
            }
            // Report linesense every second
            if (logTimer.update(ts)) {
                for (int line; line < LINE_COUNT; line++) {
                    int a = analogRead(sLineStates[line]);
                    float v = (5.0f * a) / ((1 << 10) - 1);
                    serial_printfln("LINESENSE%d: %u (%.2fV)", (line + 1), a, v);
                }
            }
        }

#define PIN_RO 0
#define PIN_RW 1

        const struct {
            const char* name;
            uint8_t pin;
            uint8_t flags;
        } pinTable[] = {                           //
            {"SW1", SW1_PIN, PIN_RO},              //
            {"SW2", SW2_PIN, PIN_RO},              //
            {"RELAY1_EN", RELAY1_EN_PIN, PIN_RW},  //
            {"RELAY2_EN", RELAY2_EN_PIN, PIN_RW},  //
            {"POWER_DIS", POWER_DIS_PIN, PIN_RW},  //
            {"LED_RED", LED_RED_PIN, PIN_RW}};
        const int pinCount = sizeof(pinTable) / sizeof(pinTable[0]);

        const char* cmd = serial_read_line();
        if (!cmd) return;

        if (!strcmp(cmd, "HELP")) {
            serial_println("LINE");
            serial_println("LINELOG");
            serial_println("RING");
            serial_println("TONE");
            for (int i = 0; i < pinCount; i++) {
                if (pinTable[i].flags & PIN_RW) {
                    serial_printfln("%s [1|0]", pinTable[i].name);
                } else {
                    serial_println(pinTable[i].name);
                }
            }
            serial_println("EXIT");
            serial_println("HELP");

        } else if (!strcmp(cmd, "TONE")) {
            if (tone_is_enabled()) {
                tone_disable();
            } else {
                tone_enable();
            }
        } else if (!strcmp(cmd, "LINE")) {
            // Report line state
            updateLineStates();
            for (int line; line < LINE_COUNT; line++) {
                serial_printfln("LINESTATE%d: %s", (line + 1), lineStateToStr(sLineStates[line]));
                serial_printfln("LINESENSE%d: %.2fV", (line + 1), sLineSenseVoltages[line]);
            }
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
                    if (*cmd && (pinTable[i].flags & PIN_RW)) {
                        digitalWrite(pinTable[i].pin, atoi(cmd));
                    }
                    serial_printfln("%s: %u", pinTable[i].name, digitalRead(pinTable[i].pin));
                    break;
                }
            }
        }
        serial_println(">");
    }
    if (stage == LEAVE) {
        digitalWrite(LED_RED_PIN, LOW);
        digitalWrite(RELAY1_EN_PIN, LOW);
        digitalWrite(RELAY2_EN_PIN, LOW);
        digitalWrite(POWER_DIS_PIN, HIGH);
    }

#undef PIN_RO
#undef PIN_RW
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
