#!/usr/bin/sh
AS2FM_PKG=../../src/as2fm
../../src/as2fm
code2flow \
$AS2FM_PKG/jani_generator/main.py \
$AS2FM_PKG/jani_generator/scxml_helpers/top_level_interpreter.py \
$AS2FM_PKG/jani_generator/scxml_helpers/scxml_to_jani.py \
$AS2FM_PKG/jani_generator/scxml_helpers/scxml_event_processor.py \
$AS2FM_PKG/jani_generator/scxml_helpers/scxml_to_jani_interfaces.py \
$AS2FM_PKG/jani_generator/ros_helpers/ros_communication_handler.py \
$AS2FM_PKG/jani_generator/jani_entries/jani_helpers.py \
$AS2FM_PKG/scxml_converter/scxml_entries/scxml_root.py \
$AS2FM_PKG/as2fm_common/ecmascript_interpretation.py
