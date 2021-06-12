#include <stdlib.h>
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <sys/random.h>
#include <sys/stat.h>
#include <stdbool.h>
#include <ctype.h>
#include <stdint.h>

#define DATADIR "./data"

#include "session.h"

static const char alpha[] = "NichL4ngSnack3nK0ppInnNacken";
static const char seedxor[] = "Buddels";

typedef uint64_t state_t[2];


static void gen_secret(char *buf, size_t buflen, const char *seed, size_t seed_size) {
	unsigned s = 0;
	for(size_t i = 0; i < seed_size; i++){
		char c = seed[i];
		c ^= seedxor[i%sizeof(seedxor)];
		s ^= c<<(8*(i%sizeof(s)));
	}
	srand(s);
	size_t len = strlen(alpha);
	for (size_t i = 0; i < buflen; i++) {
		buf[i] = alpha[random() % len];
	}
}


int session_create(struct session_id *sid){
	char seed[19];
	if (getrandom(&seed, sizeof(seed), 0) != sizeof(seed)) return -1;

	int datadir = open(DATADIR, O_RDONLY | O_DIRECTORY);
	if(datadir == -1) return -1;

	int pubdir = -1;
	int secretdir = -1;
	for(;;){
		gen_secret(sid->pub, sizeof(sid->pub), seed, sizeof(seed));
		sid->pub[sizeof(sid->pub)-1] = 0;

		gen_secret(sid->secret, sizeof(sid->secret), sid->pub, sizeof(sid->pub));
		sid->secret[sizeof(sid->secret)-1] = 0;

		int res = mkdirat(datadir, sid->pub, 0700);
		if(res == -1 && errno == EEXIST) continue;
		if(res == -1) goto fail;
		break;
	}

	pubdir = openat(datadir, sid->pub, O_RDONLY | O_DIRECTORY);
	if(pubdir == -1) goto fail;

	int res = mkdirat(pubdir, sid->secret, 0700);
	if(res == -1) goto fail;
	secretdir = openat(pubdir, sid->secret, O_RDONLY | O_DIRECTORY);
	if(secretdir == -1) goto fail;

	close(pubdir);
	close(datadir);
	return secretdir;
	
fail:;
	int oe = errno;
	if(secretdir != -1) close(secretdir);
	if(pubdir != -1) {
		unlinkat(pubdir, sid->secret, AT_REMOVEDIR);
		close(pubdir);
	}
	if(datadir != -1) {
		unlinkat(datadir, sid->pub, AT_REMOVEDIR);
		close(datadir);
	}
	errno = oe;
	return -1;
}

static bool nameok(const char *relpath, size_t bufsize){
	size_t len = strnlen(relpath, bufsize);
	if(len != bufsize - 1) return false;
	for(size_t i=0; i<len; i++){
		if(!isalnum(relpath[i])) return false;
	}
	return true;
}

int session_open(const struct session_id *sid){
	if(!nameok(sid->pub, sizeof(sid->pub)) || !nameok(sid->secret, sizeof(sid->secret))){
		errno = EINVAL;
		return -1;
	}
	char path[sizeof(DATADIR)-1+1+sizeof(sid->pub)-1+1+sizeof(sid->secret)-1+1];
	sprintf(path, "%s/%s/%s", DATADIR, sid->pub, sid->secret);
	return open(path, O_RDONLY|O_DIRECTORY);

}

static void XorShift128(state_t state) {
	uint64_t s1 = state[0];
	uint64_t s0 = state[1];
	state[0] = s0;
	s1 ^= s1 << 23;
	s1 ^= s1 >> 17;
	s1 ^= s0;
	s1 ^= s0 >> 26;
	state[1] = s1;
}

// currently the public part has to little entropy to crack this
__attribute__((unused)) static uint64_t randint64(state_t s) {
	XorShift128(s);
	return s[0] + s[1];
}
