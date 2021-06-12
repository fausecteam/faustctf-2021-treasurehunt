#include <wchar.h>
#include <string.h>
#include <stdio.h>
#include <stdint.h>
#include <math.h>
#include <stdbool.h>
#include <stdlib.h>
#include <dirent.h>
#include <fcntl.h>
#include <errno.h>
#include <inttypes.h>
#include <locale.h>

#include "map.h"

static const size_t WIDTH = 120;
static const size_t HEIGHT = 60;

static const wchar_t symbols_land[] = L"X$💰";
static const wchar_t symbols_water[] = L"X$🚣⛵";

static wchar_t symbol(treasure_t treasure, bool water){
	uint32_t i = (uint32_t) treasure.row;
	uint32_t j = (uint32_t) treasure.col;
	const wchar_t *table = water ? symbols_water : symbols_land;
	uint32_t h = (i ^ L'‰') * 12345 + (j ^ L'‽') * 1337 + (uint32_t)water * '~';
	return table[h % wcslen(table)];
}


int draw_map(treasure_t* treasures, size_t ntreasures, FILE *out){
	bool island[HEIGHT][WIDTH];
	wchar_t map[HEIGHT][WIDTH];

	char *oldlocale = setlocale(LC_CTYPE, NULL);
	if(oldlocale != NULL) oldlocale = strdup(oldlocale);
	if(oldlocale == NULL) return -1;

	if(setlocale(LC_CTYPE, "C.UTF-8") == NULL) goto fail;

	for (size_t i=0; i<HEIGHT; i++) for(size_t j=0; j<WIDTH; j++){
		double y = ((double)i-HEIGHT/2)*1.0/(HEIGHT/2);
		double x = ((double)j-WIDTH/2)*1.0/(WIDTH/2);
		double a = atan2(y, x);
		double h = 1-(x*x*1.5 + y*y*2) + cos(-13 * a)/13 + cos(5*a+6)/5;
		island[i][j] = h >= 0;
		map[i][j] = island[i][j] ? L'#' : L'~';
	}
	for(size_t ti = 0; ti < ntreasures; ti++){
		const treasure_t *t = treasures+ti;
		if(t->row >= HEIGHT) continue;
		if(t->col >= WIDTH) continue;
		map[t->row][t->col] = symbol(*t, !island[t->row][t->col]);
	}

	for (size_t i=0; i<HEIGHT; i++){
		for(size_t j=0; j<WIDTH; j++){
			char buf[20] = "x🚽†"; // a WC-tomb
			char *utf8 = buf+1;
			int len = wctomb(utf8, map[i][j]);
			utf8[len] = 0; // if wctomb fails, the wc-tomb is visible
			if(fputs(utf8, out) == EOF) return -1;
		}
		if(fputc('\n', out) == EOF) return -1;
	}
	setlocale(LC_CTYPE, oldlocale);
	free(oldlocale);
	return 0;
fail:;
	 int oe = errno;
	setlocale(LC_CTYPE, oldlocale);
	free(oldlocale);
	 errno = oe;
	 return -1;
}

static bool parse(const char *s, treasure_t *t){
	int res = sscanf(s,"%" SCNu32 ",%" SCNu32, &t->row, &t->col);
	return res == 2;
}

static int filter(const struct dirent *d){
	treasure_t t;
	return parse(d->d_name, &t);
}

static void freenthings(int n, void **ptrs){
	if(ptrs == NULL) return;
	for(int i=0; i<n; i++) free(ptrs[i]);
	free(ptrs);
}

int list_treasures(int dir, treasure_t **ts){
	struct dirent **namelist = NULL;
	int n = scandirat(dir, ".", &namelist, filter, alphasort);
	if(n == -1) return -1;
	*ts = calloc(n, sizeof(treasure_t));
	if(*ts == NULL) goto fail;
	for(int i=0; i<n; i++){
		parse((*namelist)[i].d_name, *ts + i);
	}
	freenthings(n, (void*)namelist);
	return n;
fail:;
	 int oe = errno;
	 freenthings(n, (void*)namelist);
	 errno = oe;
	 return -1;
}

int dir_map(int dirfd, FILE *out){
	treasure_t *ts;
	int nts = list_treasures(dirfd, &ts);
	if(nts == -1) return -1;
	int res = draw_map(ts, nts, out);
	int oe = errno;
	free(ts);
	errno = oe;
	return res;
}
