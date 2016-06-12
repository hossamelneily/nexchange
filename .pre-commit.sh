#!/bin/sh
wercker build --direct-mount --pipeline static-validation && wercker build --direct-mount --pipeline tests
