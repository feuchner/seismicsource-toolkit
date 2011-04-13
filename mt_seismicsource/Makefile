TARGET_DIR=$(HOME)/.qgis/python/plugins/mt_seismicsource
MAIN_DIALOG_NAME=ui_seismicsource
ANALYZE_ZONES_DIALOG_NAME=ui_zone_analysis

default: all

all:
	pyuic4 -o $(MAIN_DIALOG_NAME).py $(MAIN_DIALOG_NAME).ui
	pyuic4 -o $(ANALYZE_ZONES_DIALOG_NAME).py $(ANALYZE_ZONES_DIALOG_NAME).ui
	mkdir -p $(TARGET_DIR)
	rsync -aC . $(TARGET_DIR)
