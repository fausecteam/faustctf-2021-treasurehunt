CFLAGS = -pedantic -static -Wall -Werror -Wextra -D_FORTIFY_SOURCE=2 -O3 -fPIC -fstack-protector-all -pie -s -D _GNU_SOURCE
LIBS = -lm

.PHONY: all clean

all: treasurehunt

treasurehunt: helloworld.c log.c session.c map.c
	$(CC) $(CFLAGS) -o $@ $^ $(LIBS)

clean:
	$(RM) -f treasurehunt
