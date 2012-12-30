TEMPLATES = $(wildcard *.tdl)
IMAGES = $(patsubst %.tdl, %.xml, $(TEMPLATES))
OZ_INSTALL = oz-install -u -t 3600

all: $(IMAGES)

%.xml: %.tdl
	$(OZ_INSTALL) -x $@ $<
