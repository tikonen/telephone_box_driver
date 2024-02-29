# Telephone box driver firmware.

Firmware runs on an Arduino and controls a board for interfacing a classic rotary
dial phone. Serial parameters: 57600-8-N-1

## Led signals

* Yellow - On when phone Off-hook
* Red - On when phone is ringing
* Green - On: Device ready. Blinking: dial error and phone must be hang up to reset the error.

Simultaneous alternate blinking of Red and Green indicates self-test failure.

## Serial command interface

### Commands

**`RING\r\n`**

Rings phone until one of following conditions is true
* `STOP` command is received
* Timeout is reached (30 seconds nominally)
* Phone is picked up

Response: `OK`
<br>States: IDLE

**`STOP\r\n`**

Stop ringing the phone and return to IDLE state

Response: `OK`
<br>States: RING

**`STATE\r\n`**
Print current state

Response: `STATE` _state_
<br>States: Any

**`LINE\r\n`**
Print current line status

Response: `LINE` _status_
<br>States: Any

**`CONF <param1> <param2> ...\r\n`**
Board configuration.

Parameters
*  `DM:<n>`         int. 0 disable, 1: single digit dial (default)
*  `TON:<voltage>`  float. On-hook threshold voltage level
*  `TOFF:<voltage>` float. Off-hook threshold voltage level.
*  `HZ:<freq>`      int. Ringing frequency

Response: Current configuration when run without parameters
<br>States: IDLE

**`TERMINAL\r\n`**
Debug terminal mode

States: IDLE

**`\r\n`**
Does nothing

Response: None (just the `READY` prompt)
<br>States: Any

### Prompts

**`READY\r\n`**
Prompt that indicates device is ready to receive a next command.

States: Any

**`OK\r\n`**
Command received and accepted. If command produces any output it will be sent after this prompt.

States: Any

**`INVALID\r\n`**
Command not recognized or cannot be executed in current state.

States: Any

### Responses and Events

**`INFO <txt>\r\n`**
Informational and debug printout

States: Any

**`TEST <txt>\r\n`**
Self test result

States: INITIAL (bootup)

**`DIAL_BEGIN\r\n`**
Number dial sequence started by the phone user.

States: DIAL

**`DIAL <digit>\r\n`**
A number was succesfully dialed.

States: DIAL

**`DIAL_ERROR\r\n`**
User dialed number incorrectly (intentionally or timed out).
Phone must be put back on-hook for at least a half a second to reset error condition.

States: DIAL

**`RING_TRIP\r\n`**
Ringing phone was picked up.

States: RING

**`RING\r\n`**
Phone is currently in active period of the ringing cycle (ringing bell)

States: RING

**`RING_PAUSE\r\n`**
Phone is currently in passive period of the ringing cycle (silent)

States: RING

**`RING_TIMEOUT\r\n`**
Phone was not picked up in the maximum allowed ringing time.

States: RING

**`ERROR\r\n`**
Non-recoverable device failure. No further commands are processed.

States: Any

**`STATE <state>\r\n`**
Current state of the device. Printed out on request and always when the state changes.

States: Any

**`LINE <status>\r\n`**
Current status of the line. (ONHOOK, OFFHOOK, SHORT). Printed on request and together with selected state changes.

States: Any


## Device states

**`INITIAL`**
Bootup and self-test phase
Audio not available.

**`IDLE`**
Phone is sitting idly on-hook.
Audio not active (handset is on hook).

**`RING`**
Phone is ringing on-hook.

**`WAIT`**
Phone is off-hook (user has picked up the phone).
Play standard line tone to indicate a working phone for the user. (beeeeeeeep...)
Audio active.

**`DIAL`**
User has started to select a number. After selecting a digit the device returns to `WAIT` state.
Stop playing line tone on first digit dial.
Audio active and should not be used with high volume as it may confuse the logic counting the dial pulses from the phone.

**`DIAL_ERROR`**
Dialing failed. User must put phone back on-hook to reset the error.
Play standard error tone. (beep-beep-beep-beep)
Audio active.

**`RING`**
Phone is ringing. Returns to `IDLE` if ring timeouts (nobody picked up phone within timelimit) or to `WAIT` when phone is picked up.
Audio not active (physically disconnected).
