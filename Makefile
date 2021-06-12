SERVICE := treasurehunt
DESTDIR ?= dist_root
SERVICEDIR ?= /srv/$(SERVICE)

.PHONY: build test install

build:
	$(MAKE) -C src

test:
	python3 -m test.test -v

install: build
	mkdir -p $(DESTDIR)$(SERVICEDIR)
	cp src/treasurehunt $(DESTDIR)$(SERVICEDIR)/
	mkdir -p $(DESTDIR)/etc/systemd/system
	cp src/treasurehunt@.service $(DESTDIR)/etc/systemd/system/
	cp src/treasurehunt.socket $(DESTDIR)/etc/systemd/system/
	cp src/system-template.slice $(DESTDIR)/etc/systemd/system/
