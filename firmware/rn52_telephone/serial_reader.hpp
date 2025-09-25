#pragma once

#define LINE_BUFFER_LEN 80

class StreamLineReader
{
    Stream& stream;
    int parseIdx = 0;

public:
    StreamLineReader(Stream& s)
        : stream(s)
    {
    }

    char* read_line() { return parse_line(); }

protected:
    char* parse_line()
    {
        static char linebuffer[LINE_BUFFER_LEN + 1];

        for (int i = parseIdx; stream.available() > 0; i++, parseIdx++) {
            linebuffer[i] = (char)stream.read();

            if (i == LINE_BUFFER_LEN - 1) {
                linebuffer[i + 1] = '\0';
                parseIdx = 0;
                return linebuffer;
            }
            if (i > 0 && linebuffer[i] == '\n' && linebuffer[i - 1] == '\r') {
                // found end of line sequence (\r\n)

                // terminate string and clear trailing whitespace
                i -= 1;
                do {
                    linebuffer[i--] = '\0';
                } while (i >= 0 && linebuffer[i] == ' ');

                parseIdx = 0;
                return linebuffer;
            }
        }

        return NULL;
    }
};
