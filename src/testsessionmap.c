#include <stdio.h>
#include <err.h>
#include <locale.h>
#include <err.h>
#include <string.h>
#include <stdlib.h>

#include "map.h"
#include "session.h"

int main(int argc, char **argv){
	if(argc != 3){
		errx(1, "usage: see source");
	}
	struct session_id sid;
	strncpy(sid.pub, argv[1], sizeof(sid.pub)-1);
	strncpy(sid.secret, argv[2], sizeof(sid.secret)-1);
	int fd = session_open(&sid);
	if(fd == -1) err(1, "session_open");
	treasure_t *ts;
	int nts = list_treasures(fd, &ts);
	if(nts == -1) err(1, "list_treasures");
	int res = draw_map(ts, nts, stdout);
	if(res == -1) err(1, "draw");
	free(ts);
	return 0;
}

