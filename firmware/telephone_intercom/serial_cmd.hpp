#pragma once

#define SER_EOL "\r\n"

void serial_write_char(char c);
void serial_write_line(const char* msg);
void serial_write(const char* msg);
void serial_clear();
int serial_read(char* buffer, int count);
const char* serial_read_line();
void serial_echo_loop();  // debug
