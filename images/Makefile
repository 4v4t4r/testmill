M4 = m4 -I templates
IMAGES = $(patsubst %.tdl.in, %.xml, $(wildcard *.tdl.in))
OZ_INSTALL = oz-install -t 14400 -d3

all: $(IMAGES)

%.auto: %.auto.in
	$(M4) $< > $@

%.tdl: %.tdl.in
	$(M4) $< > $@

%.xml: %.auto %.tdl
	$(OZ_INSTALL) -x $@ -a $^
