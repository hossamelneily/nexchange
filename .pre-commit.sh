#!/bin/sh

wercker build --direct-mount --docker-local --pipeline static-validation &&
wercker build --direct-mount --docker-local --pipeline tests

