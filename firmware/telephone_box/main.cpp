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

// Voltage thresholds for line sense pin
#define LSENSE_V_ONHOOK 0.1
#define LSENSE_V_OFFHOOK 1.5

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
volatile LineState lineState = LINE_STATE_UNKNOWN;
static State state = STATE_INITIAL;
static State lastState = STATE_NONE;

void _putchar(char character) { serial_write_char(character); }

#define serial_printf(format, ...) printf(format SER_EOL, ##__VA_ARGS__)
#define serial_print(str) serial_write_line(str)

#define test_button() (!digitalRead(TEST_BUTTON_PIN))

static const char* stateToStr()
{
    const char* stateMap[] = {"-", "INIT", "IDLE", "RING", "WAIT", "DIAL", "DIAL2", "DIAL_ERROR", "TERMINAL"};

    return stateMap[state];
}

bool setState(State newState)
{
    lastState = state;
    state = newState;

    if (lastState != state) {
        serial_printf("STATE %s", stateToStr());
    }
}

bool setLineState(LineState newState)
{
    LineState oldState = lineState;
    lineState = newState;

    digitalWrite(LED_YELLOW, lineState == LINE_STATE_OFF_HOOK);

    return oldState != lineState;
}

static bool runSelfTest();

static struct Configuration {
    bool singleDigitDial = true;
} configuration;

/*
static volatile bool ring_trip = false;

// executed about 60 times per second to poll status of sense pins.
// TODO: It would be better to implement this check as an interrupt but
// the current pin may not support an interrupt
static void pollTripStatus()
{
    if (!digitalRead(PSENSE_PIN)) {
        // ring trip has triggered, disconnect ringing immediately.
        digitalWrite(RING_EN_PIN, LOW);
        ring_trip = true;
        digitalWrite(LED_YELLOW, HIGH);
    }
}


void configurePollTimer()
{
    // 8-bit Timer 2 in normal mode counts to 0xFF.
    // Hz in milliseconds is
    // f = F_CPU / (256 * prescaler)
    // 1024 prescaler gives 61Hz, ~16.4ms period
    TCCR2A = 0;
    TCCR2B = _BV(CS22) | _BV(CS21) | _BV(CS20);  // 1024 prescaler
}

void enablePollTimer(bool enabled)
{
    if (enabled) {
        TIMSK2 = _BV(TOIE2);  // Overflow interrupt enable
    } else {
        TIMSK2 &= ~_BV(TOIE2);  // Overflow interrupt disable
    }
}

ISR(TIMER2_OVF_vect)
{
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
    // PORTB ^= _BV(5);  // Toggle pin 13 (LED_BUILTIN)
    pollTripStatus();
}
*/

void setup()
{
    pinMode(LED_BUILTIN, OUTPUT);
    pinMode(LED_RED, OUTPUT);
    pinMode(LED_GREEN, OUTPUT);
    pinMode(LED_YELLOW, OUTPUT);
    digitalWrite(LED_BUILTIN, HIGH);
    digitalWrite(LED_RED, HIGH);
    digitalWrite(LED_GREEN, HIGH);
    digitalWrite(LED_YELLOW, HIGH);
    delay(500);
    digitalWrite(LED_BUILTIN, LOW);
    digitalWrite(LED_RED, LOW);
    digitalWrite(LED_GREEN, LOW);
    digitalWrite(LED_YELLOW, LOW);

    Serial.begin(57600);
    // serial_echo_loop();  // Debug serial command interface

    digitalWrite(LED_DEBUG, LOW);
    pinMode(TEST_BUTTON_PIN, INPUT_PULLUP);

    pinMode(HB_OUT1_PIN, OUTPUT);
    pinMode(HB_OUT2_PIN, OUTPUT);
    pinMode(RING_EN_PIN, OUTPUT);
    pinMode(PWM_PIN, OUTPUT);
    digitalWrite(HB_OUT1_PIN, LOW);
    digitalWrite(HB_OUT2_PIN, LOW);
    digitalWrite(RING_EN_PIN, LOW);
    digitalWrite(PWM_PIN, LOW);

    pinMode(LSENSE_PIN, INPUT);
    analogReference(DEFAULT);  // 5V
    analogRead(LSENSE_PIN);    // First analog read must be discarded
    pinMode(PSENSE_PIN, INPUT);

    // configurePollTimer();

    digitalWrite(LED_GREEN, HIGH);
    if (!runSelfTest()) {
        // Indicate problem by blinking leds
        while (true) {
            serial_print("ERROR");
            digitalWrite(LED_GREEN, !digitalRead(LED_GREEN));
            digitalWrite(LED_RED, !digitalRead(LED_RED));
            delay(500);
        }
    }
}

bool isRingTrip() { return !digitalRead(PSENSE_PIN); }

LineState readLineState()
{
    const float vref = 5.0f;
    const int amax = (1 << 10) - 1;

    int lsense = analogRead(LSENSE_PIN);
    float v = (vref * lsense) / amax;
    if (v <= LSENSE_V_ONHOOK) return LINE_STATE_ON_HOOK;
    if (v <= LSENSE_V_OFFHOOK) return LINE_STATE_OFF_HOOK;
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

    LineState lineState = readLineState();
    serial_printf("INFO Line state: %s", lineStateToStr(lineState));

    bool lineSenseCheck = (lineState == LINE_STATE_ON_HOOK);
    serial_printf("TEST Line sense: %s", lineSenseCheck ? "PASS" : "FAULT");
    pass = pass && lineSenseCheck;

    digitalWrite(RING_EN_PIN, HIGH);
    delay(100);
    bool tripCheck = !isRingTrip();
    serial_printf("TEST Ring-trip: %s", tripCheck ? "PASS" : "FAIL");

    pass = pass && tripCheck;

    digitalWrite(RING_EN_PIN, LOW);

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
            serial_printf("LINE %s", lineStateToStr(lineState));
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

bool parse_and_apply_config(const char* conf)
{
    if (*conf == '\0') {
        // print current configuration
        serial_printf("CONF %s%d", "DM:", configuration.singleDigitDial);
        return true;
    } else if (*conf == ' ') {
        conf++;
        // Dial mode configuration
        if (!strncmp(conf, "DM:", 3)) {
            conf += 3;
            char* endptr = NULL;
            int val = strtol(conf, &endptr, 10);
            if (*endptr == '\0') {
                serial_print("OK");
                configuration.singleDigitDial = val;
                return true;
            }
        }
    }
    serial_print("INVALID");
    return false;
}

void handle_state_idle(StateStage stage)
{
    static Timer2 waitTimer(false, 200);
    uint32_t ts = millis();

    if (stage == ENTER) {
        serial_clear();
        serial_print("READY");
        waitTimer.reset(ts);
    }

    if (stage == EXECUTE) {
        updateLineState();

        // Phone is off-hook
        if (lineState == LINE_STATE_OFF_HOOK) {
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
            // wait until user releases button
            while (!test_button())
                ;
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
                parse_and_apply_config(cmd + 4);
            } else {
                serial_print("INVALID");
            }
            serial_print("READY");
        }
    }
}

void handle_state_ring(StateStage stage)
{
    // TODO experiment with PWM drive Sine wave. See nano_pwm_dac example.

    static bool ringState = false;

    static Timer2 ringingTimeout(false, 30000);
    static Timer2 ringTime(false, RING_TIMEMS);
    static Timer2 ringPauseTime(false, RING_PAUSEMS);
    static Timer2 ringHzTimer(true, 1000 / RING_FREQ_HZ / 2);
    static Timer2 periodTimer(true, 1000 / RING_FREQ_HZ / 2 * RING_PWM_DUTY);
    // static Timer2 ringTripTimer(false, 10);

    uint32_t ms = millis();

    if (stage == ENTER) {
        // enablePollTimer(true);
        updateLineState();

        if (lineState != LINE_STATE_ON_HOOK) {
            setState(STATE_IDLE);
            return;
        }

        ringingTimeout.reset(ms);
        ringTime.reset(ms);
        ringPauseTime.reset(ms);
        ringHzTimer.reset(ms);
        periodTimer.reset(ms);

        serial_print("READY");

        digitalWrite(HB_OUT1_PIN, LOW);
        digitalWrite(HB_OUT2_PIN, LOW);
        digitalWrite(RING_EN_PIN, HIGH);
        digitalWrite(PWM_PIN, HIGH);
        wait_ms(RELAY_DELAY_MS);  // let relay latch before starting ring AC generation

        ringState = true;
        serial_print("RING");
        // ringTripTimer.reset(ms);
    }

    if (stage == EXECUTE) {
        bool ring_trip = !digitalRead(PSENSE_PIN);
        if (ring_trip) {
            // phone has been picked up
            serial_print("RING_TRIP");
            serial_print("LINE OFF_HOOK");
            setState(STATE_WAIT);
            return;
        }

        /*
        if (ring_trip) {
            if (ringTripTimer.update(ms)) {
                // phone has been picked up
                serial_print("RING_TRIP");
                setState(STATE_WAIT);
                return;
            }
        } else {
            ringTripTimer.reset(ms);
        }
        */

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

        if (ringingTimeout.update(ms)) {
            serial_print("RING_TIMEOUT");
            setState(STATE_IDLE);
            return;
        }

        if (ringState) {
            // phone is ringing
            if (ringTime.update(ms)) {
                // ring cycle expired, go to wait time
                digitalWrite(HB_OUT1_PIN, LOW);
                digitalWrite(HB_OUT2_PIN, LOW);
                digitalWrite(LED_RED, LOW);
                ringState = 0;
                serial_print("RING_PAUSE");
                ringPauseTime.reset(ms);
            } else {
                // ring cycle active
                if (ringHzTimer.update(ms)) {
                    digitalWrite(HB_OUT1_PIN, ringHzTimer.flipflop());
                    digitalWrite(HB_OUT2_PIN, !ringHzTimer.flipflop());
                    periodTimer.reset(ms);

                    digitalWrite(LED_RED, HIGH);
                }
                if (periodTimer.update(ms)) {
                    // Period reached
                    digitalWrite(HB_OUT1_PIN, LOW);
                    digitalWrite(HB_OUT2_PIN, LOW);
                    digitalWrite(LED_RED, LOW);
                }
            }
        } else if (ringPauseTime.update(ms)) {
            ringState = true;
            serial_print("RING");
            ringTime.reset(ms);
        }
    }

    if (stage == LEAVE) {
        digitalWrite(LED_RED, LOW);
        digitalWrite(HB_OUT1_PIN, LOW);
        digitalWrite(HB_OUT2_PIN, LOW);
        digitalWrite(RING_EN_PIN, LOW);
        digitalWrite(PWM_PIN, LOW);
        // enablePollTimer(false);
        digitalWrite(LED_BUILTIN, LOW);

        // Wait a little so that the line state has time to stabilize
        // after the relay opens
        delay(RELAY_DELAY_MS);
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
    }

    if (stage == EXECUTE) {
        discardCommands();
        updateLineState();

        // Wait for the number dial in
        if (lineState == LINE_STATE_ON_HOOK) {
            serial_print("LINE ON_HOOK");
            setState(STATE_IDLE);
            return;
        } else if (lineState == LINE_STATE_SHORT) {
            // dial begins
            if (configuration.singleDigitDial) {
                setState(STATE_DIAL);
            } else {
                setState(STATE_DIAL2);
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
                } else if (lineState == LINE_STATE_ON_HOOK) {
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
                    if (lineState == LINE_STATE_ON_HOOK && !pulseDetected) {
                        dialPulses++;
                        pulseDetected = true;
                        numberTimeout.reset();
                    }
                    if (lineState == LINE_STATE_OFF_HOOK && pulseDetected) {
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
                if (lineState == LINE_STATE_ON_HOOK) {
                    // user has closed the phone
                    serial_print("LINE ON_HOOK");
                    digits = 0;
                    state = DONE;
                }
                if (lineState == LINE_STATE_SHORT) {
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
                } else if (lineState == LINE_STATE_ON_HOOK) {
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
                    if (lineState == LINE_STATE_ON_HOOK && !pulseDetected) {
                        dialPulses++;
                        pulseDetected = true;
                        numberTimeout.reset();
                    }
                    if (lineState == LINE_STATE_OFF_HOOK && pulseDetected) {
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

void handle_state_error(StateStage stage)
{
    static Timer2 errorClearTimeout(false, 1000);
    static Timer2 blinkTimer(true, 200);
    uint32_t ts = millis();

    if (stage == ENTER) {
        errorClearTimeout.reset(ts);
    }

    if (stage == EXECUTE) {
        if (blinkTimer.update(ts)) {
            digitalWrite(LED_GREEN, blinkTimer.flipflop());
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
        if (lineState == LINE_STATE_ON_HOOK) {
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
        digitalWrite(LED_GREEN, HIGH);
    }
}

void handle_state_terminal(StateStage stage)
{
    static bool linelog = false;

    if (stage == ENTER) {
        digitalWrite(LED_GREEN, HIGH);
        digitalWrite(LED_YELLOW, HIGH);
        digitalWrite(LED_RED, HIGH);
        serial_print("Testing terminal");
        serial_print(">");
        linelog = false;
    }
    if (stage == EXECUTE) {
        if (linelog) {
            // Log line state every time it changes
            if (updateLineState()) {
                serial_printf("LINESTATE: %s", lineStateToStr(lineState));
            }
        }

        const char* cmd = serial_read_line();
        if (!cmd) return;

        if (!strcmp(cmd, "HELP")) {
            serial_print("LINE");
            serial_print("LINELOG [1|0]");
            serial_print("LED [Y|G|R]");
            serial_print("RING");
            serial_print("RING_EN [1|0]");
            serial_print("EXIT");
            serial_print("HELP");

        } else if (!strcmp(cmd, "LINE")) {
            // Report line state
            updateLineState();
            serial_printf("LINESTATE: %s", lineStateToStr(lineState));
            int a = analogRead(LSENSE_PIN);
            serial_printf("LSENSE: %u", a);
            serial_printf("PSENSE: %u", digitalRead(PSENSE_PIN));
        } else if (!strncmp(cmd, "LINELOG ", 8)) {
            // Toggle line state logging
            linelog = !linelog;
            serial_printf("LINELOG: %d", linelog);
        } else if (!strncmp(cmd, "LED ", 4)) {
            // Toggle leds
            cmd += 4;
            if (!strncmp(cmd, "Y", 1)) {
                digitalWrite(LED_YELLOW, !digitalRead(LED_YELLOW));
            } else if (!strncmp(cmd, "R", 1)) {
                digitalWrite(LED_RED, !digitalRead(LED_RED));
            } else if (!strncmp(cmd, "G", 1)) {
                digitalWrite(LED_GREEN, !digitalRead(LED_GREEN));
            } else {
                serial_print("INVALID");
            }
        } else if (!strcmp(cmd, "RING")) {
            setState(STATE_RING);
            return;
        } else if (!strncmp(cmd, "RING_EN ", 8)) {
            // Enable or disable ring
            cmd += 8;
            digitalWrite(RING_EN_PIN, atoi(cmd));
            serial_printf("RING_EN: %u", digitalRead(RING_EN_PIN));
        } else if (!strcmp(cmd, "EXIT")) {
            setState(STATE_WAIT);
            return;
        }
        serial_print(">");
    }
    if (stage == LEAVE) {
        digitalWrite(LED_GREEN, HIGH);
        digitalWrite(LED_YELLOW, LOW);
        digitalWrite(LED_RED, LOW);
        digitalWrite(RING_EN_PIN, LOW);
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
StateHandler stateHandlers[] = {
    handle_state_none,
    handle_state_initial,
    handle_state_idle,
    handle_state_ring,
    handle_state_wait,
    handle_state_dial,
    handle_state_dial2,
    handle_state_error,
    handle_state_terminal
};
// clang-format on

void loop()
{
    if (lastState != state) {
        State prevState = lastState;
        lastState = state;
        stateHandlers[prevState](LEAVE);
        stateHandlers[state](ENTER);
    } else {
        stateHandlers[state](EXECUTE);
    }
}
