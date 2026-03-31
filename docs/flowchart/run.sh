#!/usr/bin/sh
AS2FM_PKG=../../src/as2fm

code2flow \
-o main_scxml_to_jani.svg \
--target-function main_scxml_to_jani \
--upstream-depth 2 \
--downstream-depth 2 \
$AS2FM_PKG/*
