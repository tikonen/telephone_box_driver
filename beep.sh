#!/bin/bash

# Script accepts same arguments as linux beep command and outputs a raw table or a C/C++ header
# with the tones and durations.
#
# Env variables
# BEEP_EXPORT_RAW     If defined data is exported as raw table
# BEEP_EXPORT_PREFIX  Exported C header variables are prefixed with this string
#

POSITIONAL_ARGS=()
FREQS=()
DURATIONS=()

set_defaults() {
  REPEATS="1"
  DELAY="0"
  FREQ=440
  DURATION=200
  DELAYLASTSKIP=0
}

add_note () {
  FREQS+=("$1")
  DURATIONS+=("$2")

  if [[ "$3" -gt 0 ]]; then # delay
    FREQS+=("0")
    DURATIONS+=("$3")
  fi
}

add_repeated_note() {
  if [ $REPEATS -gt 1 ]; then
    for i in $(seq $REPEATS); do
      local _DELAY=$DELAY
      if [[ $DELAYLASTSKIP = 1 && $i = $REPEATS ]]; then
        _DELAY=0 # skip delay on last repeat
      fi
      add_note ${FREQ} ${DURATION} ${_DELAY}
    done
  else
    # delay is never skipped on a single repeat
    add_note ${FREQ} ${DURATION} ${DELAY}
  fi
}

# Parses command line chain of Linux beep command
# beep -f 220 -d 250 -n -f 220 -d 250 -n -f 261 -d 250 -n -f 22..

set_defaults

while [[ $# -gt 0 ]]; do
  case $1 in
    -f)
      FREQ="${2%.*}"  # match float to integer
      shift # pass argument
      shift # pass value
      ;;
	  -r)
	    REPEATS="${2%.*}"
      shift
      shift
      ;;
    -l)
      DURATION="${2%.*}"
      shift
      shift
      ;;
    -D)
      DELAY="${2%.*}"
      shift
      shift
        ;;
    -d)
      DELAY="${2%.*}"
      DELAYLASTSKIP=1
      shift
      shift
      ;;
    -n)
      # next
      add_repeated_note
      set_defaults

      shift
      ;;
    -*|--*)
      echo "Unknown option $1"
      exit 1
      ;;
    *)
      POSITIONAL_ARGS+=("$1") # save positional arg
      shift
      ;;
  esac
done

# add the last note that was not followed by the '-n' argument
add_repeated_note

if [[ -v BEEP_EXPORT_RAW ]]; then
  len=${#FREQS[@]}
  for((i=0; i<$len; i++)); do
    echo "${FREQS[$i]} ${DURATIONS[$i]}"
  done
else
  # Output a C/C++ header file
  COUNT=${#DURATIONS[@]}
  echo "#pragma once"
  echo  "//" $((4 * $COUNT + 2)) "bytes"
  echo "// clang-format off"
  #echo -n "// " ; date
  printf -v joined '%s, ' "${FREQS[@]}"
  echo "const uint16_t ${BEEP_EXPORT_PREFIX}notes[${COUNT}] PROGMEM = { ${joined%,} };"
  printf -v joined '%s, ' "${DURATIONS[@]}"
  echo "const uint16_t ${BEEP_EXPORT_PREFIX}durations[${COUNT}] PROGMEM = { ${joined%,} };"
  echo "const uint16_t ${BEEP_EXPORT_PREFIX}noteCount = ${COUNT};"
  echo "// clang-format on"
fi