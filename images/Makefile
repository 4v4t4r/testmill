TEMPLATES = $(wildcard *.tdl)
IMAGES = $(patsubst %.tdl, %.xml, $(TEMPLATES))
OZ_INSTALL = oz-install -u -t 14400 -d3

all: $(IMAGES)

%.xml: %.tdl
	$(OZ_INSTALL) $(shell ./findauto.py $<) -x $@ $<
