#include "log.h"

FILE *log_stream;

void init_log() {
  log_stream = fopen(LOGFILE, "a");
  logd("log initialized\n");
}
