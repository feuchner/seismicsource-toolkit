SUBDIRS=AtticIvy

TARGET ?= all

###  Build rules
.PHONY: default all $(SUBDIRS)

###### Default Rules (no target is provided)
default: all

###### All Rules 
all: $(SUBDIRS)

$(SUBDIRS):
	if test -d $@; then \
		cd $@; $(MAKE) all; \
	fi
