#include <stdio.h>
#include <err.h>
#include <locale.h>
#include "map.h"


int main(){
	treasure_t ts[] = {{3,3}, {10, 20}, {0,1}, {40, 30}};
	int res = draw_map(ts, sizeof(ts)/sizeof(*ts), stdout);
	if(res == -1) err(1, "draw");
	return 0;
}

