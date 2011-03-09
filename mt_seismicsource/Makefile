TARGET_DIR=$(HOME)/.qgis/python/plugins/mt_seismicsource
MAIN_DIALOG_NAME=ui_seismicsource

default: all

all:
	pyuic4 -o $(MAIN_DIALOG_NAME).py $(MAIN_DIALOG_NAME).ui
	rsync -aC . $(TARGET_DIR)
