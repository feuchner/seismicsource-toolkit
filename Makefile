ARCHIVE_FILE=mt_seismicsource/archive/toolkit-data-archive.tgz.bf
UNPACK_DIR=mt_seismicsource

SUBDIRS=mt_seismicsource

TARGET ?= all

###  Build rules
.PHONY: default all $(SUBDIRS)

###### Default Rules (no target is provided)
default: all

###### All Rules 
all: local $(SUBDIRS)

$(SUBDIRS):
	if test -d $@; then \
		cd $@; $(MAKE) all; \
	fi

local:
	openssl enc -d -blowfish -pass file:mt-symkey.bin < $(ARCHIVE_FILE) | tar -xz -C $(UNPACK_DIR)
