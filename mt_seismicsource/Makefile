TARGET_DIR=$(HOME)/.qgis/python/plugins/mt_seismicsource
MAIN_DIALOG_NAME=ui_seismicsource
SLIVER_ANALYSIS_DIALOG_NAME=ui_sliver_analysis
PLOTWINDOW_DIALOG_NAME=ui_plotwindow

SUBDIRS=code

TARGET ?= all

###  Build rules
.PHONY: default all $(SUBDIRS)

###### Default Rules (no target is provided)
default: all

###### All Rules 
all: $(SUBDIRS) local

$(SUBDIRS):
	if test -d $@; then \
		cd $@; $(MAKE) all; \
	fi

local:
	pyuic4 -o $(MAIN_DIALOG_NAME).py $(MAIN_DIALOG_NAME).ui
	pyuic4 -o $(SLIVER_ANALYSIS_DIALOG_NAME).py $(SLIVER_ANALYSIS_DIALOG_NAME).ui
	pyuic4 -o $(PLOTWINDOW_DIALOG_NAME).py $(PLOTWINDOW_DIALOG_NAME).ui
	mkdir -p $(TARGET_DIR)
	rsync -aC . $(TARGET_DIR)
