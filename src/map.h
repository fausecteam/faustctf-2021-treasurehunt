#ifndef MAP_H
#define MAP_H

#include <stdint.h>

typedef struct{
	uint32_t row, col;
} treasure_t;

/// draws a treasure array into an character map
int draw_map(treasure_t* treasures, size_t ntreasures, FILE *out);

/// searchs treasures in directory and reaturns malloced trasure array
int list_treasures(int dir, treasure_t **ts);

/// combination of them
int dir_map(int dir, FILE *out);

#endif
