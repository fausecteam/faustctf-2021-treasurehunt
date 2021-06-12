#include <stdio.h>
#include <string.h>
#include <err.h>

#include "session.h"

int main(int argc, char **argv){
	struct session_id sid;
	if(argc == 1){
		int fd = session_create(&sid);
		if(fd == -1) err(1, "session_create");
		printf("created: %s %s\n", sid.pub, sid.secret);
	}
	else if(argc == 3){
		strncpy(sid.pub, argv[1], sizeof(sid.pub));
		strncpy(sid.secret, argv[2], sizeof(sid.secret));
		int fd = session_open(&sid);
		if(fd == -1) err(1, "session_open");
	}
	else{
		errx(1, "usage: see source");
	}
	return 0;
}
