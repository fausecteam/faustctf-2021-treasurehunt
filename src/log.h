#include <stdio.h>

#ifndef LOG_H
#define LOG_H

#define DEBUG 1
#define LOGFILE "/tmp/treasurehunt.log"

extern FILE *log_stream;
#define TO_STRING_IMPL(x) #x
#define TO_STRING(x) TO_STRING_IMPL(x)

#define log(fmt, ...) \
            do { if (DEBUG && log_stream) { \
              fprintf(log_stream, fmt); \
              fprintf(log_stream, ##__VA_ARGS__); \
              fflush(log_stream); } \
            } while (0)

// Prepend file name and line number (lno) to messages:
#define loge(...) log("ERR   " __FILE__ ":" TO_STRING(__LINE__) ": ", __VA_ARGS__)
#define logi(...) log("INFO  " __FILE__ ":" TO_STRING(__LINE__) ": ", __VA_ARGS__)
#define logd(...) log("DEBUG " __FILE__ ":" TO_STRING(__LINE__) ": ", __VA_ARGS__)

void init_log(void);

#endif /*LOG_H*/

