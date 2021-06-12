#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include <stdint.h>
#include <sys/types.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>

#include "log.h"
#include "session.h"
#include "map.h"

#define NUM_PARAMS 2
#define MAX_SIZE 0x2000

#define NONE 0x00000000
#define VALUE_INPUT 0x00000001
#define VALUE_OUTPUT 0x00000002
#define VALUE_INOUT 0x00000003
#define MEMREF_INPUT 0x00000005
#define MEMREF_OUTPUT 0x00000006
#define MEMREF_INOUT 0x00000007

#define PARAM_TYPE_GET(p, i) (((p) >> (i * 4)) & 0xF)

typedef struct {
  uint64_t a;
  uint64_t b;
} value_t;

typedef struct {
  size_t off;
  size_t sz;
} memref_t;

typedef union {
  value_t value;
  memref_t memref;
} param_t;

typedef struct {
  int dirfd;
  FILE *file;
} session_t;

typedef struct __attribute__((packed)) {
  uint16_t sessCmdId;
  uint16_t cmdId;
  uint16_t paramTypes;
  param_t params[NUM_PARAMS];
  uint8_t buf[]; // data for the two params
} ctx_t;

enum SESS { SESSOPEN = 1, INVOKE, SESSCLOSE };

enum CMD { OPEN = 1337, STORE, RETRIEVE, MAP, CHECK, CLOSE };

void print_ctx(ctx_t *ctx) {
  logd("%d\n", ctx->sessCmdId);
  logd("%d\n", ctx->cmdId);
  logd("%#hx\n", ctx->paramTypes);
  logd("params[0]:\n");
  logd("%" PRIx64 "\n", ctx->params[0].value.a);
  logd("%" PRIx64 "\n", ctx->params[0].value.b);
  logd("params[1]:\n");
  logd("offset: %" PRIx64 "\n", ctx->params[1].memref.off);
  logd("size: %" PRIx64 "\n", ctx->params[1].memref.sz);
}

int get_session(ctx_t *ctx) {
  struct session_id *in_sid;
  int dirfd = -1;

  if (ctx->paramTypes == (MEMREF_OUTPUT | VALUE_OUTPUT << 4)) {
    in_sid = (struct session_id *) &ctx->buf[ctx->params[0].memref.off];
    dirfd = session_create(in_sid);
    if (dirfd > 0) {
      // OK!
      ctx->params[1].value.a = 0;
    }
  } else if (ctx->paramTypes == (MEMREF_INPUT | (VALUE_OUTPUT << 4))) {
    in_sid = (struct session_id *) &ctx->buf[ctx->params[0].memref.off];
    dirfd = session_open(in_sid);
    if (dirfd > 0) {
      // OK!
      ctx->params[1].value.a = 0;
    }
  }

  return dirfd;
}

int close_session(session_t *sess, ctx_t *ctx) {
  if (ctx->paramTypes != VALUE_OUTPUT) {
    return -1;
  }

  close(sess->dirfd);
  sess->dirfd = -1;

  ctx->params[0].value.a = 0;
  return 0;
}


size_t recv_msg(char *buf) {
  // receive data and store in buf, return number of bytes read in total
  ssize_t nread;
  ctx_t *ctx;
  size_t off = 0;
  size_t nread_total = 0;

  // receive the context
  nread = read(STDIN_FILENO, buf, sizeof(ctx_t));
  nread_total += nread;
  if (nread != sizeof(ctx_t) || nread_total > MAX_SIZE) {
    loge("read: %s", strerror(errno));
    abort();
  }

  // receive the params
  ctx = (ctx_t *) buf;
  for (int i = 0; i < NUM_PARAMS; i++) {
    char paramType = PARAM_TYPE_GET(ctx->paramTypes, i);
    switch (paramType) {
      case NONE:
        {
          // do nothing
          break;
        }
      case VALUE_INPUT:
      case VALUE_OUTPUT:
      case VALUE_INOUT:
        {
          // do nothing
          break;
        }
      case MEMREF_INPUT:
      case MEMREF_OUTPUT:
      case MEMREF_INOUT:
        {

          size_t sz = ctx->params[i].memref.sz;
          if (nread_total + sz > MAX_SIZE) {
            loge("buffer for param %d too large: %#lx\n", i, sz);
            abort();
          }


          // receive buffer for input memrefs
          if (paramType != MEMREF_OUTPUT) {
            nread = read(STDIN_FILENO, &ctx->buf[off], sz);
          } else {
            nread = sz;
          }

          nread_total += nread;
          if (nread < 0 || (size_t)nread != sz || nread_total > MAX_SIZE) {
            loge("read: %s", strerror(errno));
            abort();
          }

          ctx->params[i].memref.off = off;
          off += sz;
          break;
        }
      default:
        //loge("Format error: wrong paramType\n");
        return -1;
    };
  }

  return nread_total;
}

size_t send_msg(ctx_t *ctx) {
  ssize_t nwritten;

  nwritten = write(STDOUT_FILENO, (char*) ctx, sizeof(ctx_t));
  if (nwritten != sizeof(ctx_t)) {
    loge("write: %s", strerror(errno));
    abort();
  }

  for (int i = 0; i < NUM_PARAMS; i++) {
    char paramType = PARAM_TYPE_GET(ctx->paramTypes, i);
    switch (paramType) {
      case NONE:
        {
          // do nothing
          break;
        }
      case VALUE_INPUT:
      case VALUE_OUTPUT:
      case VALUE_INOUT:
        {
          // do nothing
          break;
        }
      case MEMREF_INPUT:
        {
          // do nothing
          break;
        }
      case MEMREF_OUTPUT:
      case MEMREF_INOUT:
        {

          size_t sz = ctx->params[i].memref.sz;
          size_t off = ctx->params[i].memref.off;
          nwritten = write(STDOUT_FILENO, (char*) &ctx->buf[off], sz);
          if (nwritten < 0 || (size_t)nwritten != sz) {
            loge("write: %s", strerror(errno));
            abort();
          }
          break;
        }
      default:
        return -1;
    };
  }

  return nwritten;
}

int invoke_command(session_t *sess, ctx_t *ctx) {
  switch (ctx->cmdId) {
  case OPEN: {
    logd("Open.\n");
    // creates global fd
    // in: memref.input -> fname -> <int>,<int>
    // out: value.out OK/FAIL
    // need to close file before opening another one
    if (sess->file != NULL) {
      // file needs to be closed first via CLOSE
      loge("File already opened.\n");
      return -1;
    }

    // check param types
    if (PARAM_TYPE_GET(ctx->paramTypes, 0) != MEMREF_INPUT ||
        PARAM_TYPE_GET(ctx->paramTypes, 1) != VALUE_OUTPUT) {
      loge("Bad param types (%#hx).\n", ctx->paramTypes);
      return -1;
    }

    char* fname = (char*) &ctx->buf[ctx->params[0].memref.off];

    // TODO(mb): sanitize string for dir traversal?
    int fd = openat(sess->dirfd, fname, O_RDWR | O_CREAT, S_IRUSR | S_IWUSR);
    if (fd < 0 ) {
      loge("openat: %s", strerror(errno));
      abort();
    }

    sess->file = fdopen(fd, "r+");
    if (sess->file == NULL) {
      loge("fdopen failed");
      abort();
    }

    // OK!
    ctx->params[1].value.a = 0x0;
    break;
  }
  case STORE: {
    // in: global fd, memref.input
    // out: value.out OK/FAIL
    logd("Store.\n");
    size_t off = ctx->params[0].memref.off;
    size_t sz = ctx->params[0].memref.sz;
    size_t nwritten = 0;

    fseek(sess->file, 0, SEEK_SET);
    nwritten = fwrite(&ctx->buf[off], 1, sz, sess->file);
    if (nwritten != sz) {
      loge("fwrite failed\n");
      abort();
    }

    // OK!
    ctx->params[1].value.a = 0;
    break;
  }
  case RETRIEVE: {
    // in: global fd, memref.output
    // out: value.out OK/FAIL
    logd("Retrieve.\n");
    size_t off = ctx->params[0].memref.off;
    size_t sz = ctx->params[0].memref.sz;
    size_t nread = 0;

    fseek(sess->file, 0, SEEK_SET);
    nread = fread(&ctx->buf[off], 1, sz, sess->file);
    if (nread != sz && ferror(sess->file)) {
      loge("fread failed\n");
      abort();
    }

    // OK!
    ctx->params[1].value.a = 0;
    break;
  }
  case CLOSE: {
    // out: value.out OK/FAIL
    logd("Close.\n");
    if (sess->file == NULL) {
      // file needs to be opened via OPEN first
      loge("File not opened yet.\n");
      return -1;
    }

    // check param types
    if (PARAM_TYPE_GET(ctx->paramTypes, 0) != VALUE_OUTPUT ||
        PARAM_TYPE_GET(ctx->paramTypes, 1) != NONE) {
      return -1;
    }

    // close file
    fclose(sess->file);
    sess->file = NULL;

    // OK!
    ctx->params[0].value.a = 0x0;
    break;
  }
  case MAP: {
	  logd("Map.\n");
	  // in: global fd, no params
	  // out: value.out OK/FAIL
	  int ok = dir_map(sess->dirfd, sess->file);
	  if(ok == -1) {
		  loge("dirmap %s", strerror(errno));
		  abort();
	  }
											
	  // OK!
	  ctx->params[1].value.a = 0;
	  break;
  }

  case CHECK: {
    logd("Check.\n");
    // out: value.out file size
    if (sess->file == NULL) {
      // file needs to be opened via OPEN first
      loge("File not opened yet.\n");
      return -1;
    }

    // check param types
    if (PARAM_TYPE_GET(ctx->paramTypes, 0) != VALUE_OUTPUT ||
        PARAM_TYPE_GET(ctx->paramTypes, 1) != NONE) {
      return -1;
    }

    // file size
	fseek(sess->file, 0, SEEK_END);
	size_t len = ftell(sess->file);

    // OK!
    ctx->params[0].value.a = len;
    break;
  }
  default:
    logd("Seemannsgarn!\n");
  }

  return 0;
}

int main(void) {
  // unbuffered stdout and stdin
  setvbuf(stdout, NULL, _IONBF, 0);
  setvbuf(stdin, NULL, _IONBF, 0);

  init_log();

  char buf[MAX_SIZE] = {0};
  ctx_t *ctx;
  session_t sess = { -1, NULL };

  while (1) {
    recv_msg(buf);
    ctx = (ctx_t *) buf;
    switch (ctx->sessCmdId) {
    case SESSOPEN: {
      logd("SessOpen.\n");
      sess.dirfd = get_session(ctx);
      if (sess.dirfd < 0) {
        loge("get_session() error\n");
        abort();
      }
      send_msg(ctx);
      break;
    }
    case INVOKE: {
      logd("Invoke.\n");
      invoke_command(&sess, ctx);
      send_msg(ctx);
      break;
    }
    case SESSCLOSE: {
      logd("SessClose.\n");
      close_session(&sess, ctx);
      send_msg(ctx);
      break;
    }
    default:
      logd("Seemannsgarn!\n");
    }
  }

  return 0;
}
