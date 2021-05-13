# Always fail shell on all errors
SHELL := /bin/bash -euo pipefail

# BEGIN Disable in-built Makefile rules
MAKEFLAGS += --no-builtin-rules
.SUFFIXES:
# END Disable in-built Makefile rules

BUILD_DIR := build

# Make sure build dir exists
$(shell mkdir -p $(BUILD_DIR))

# Look in build dir for goal files like "wheels" and Docker image
# timestamp files
VPATH=$(BUILD_DIR) dist

VERSION=$(shell cat VERSION.txt)
POLYDATUM_WHEEL=polydatum-$(VERSION)-py3-none-any.whl


.PHONY: all
all: wheel


.PHONY: wheel
wheel: $(POLYDATUM_WHEEL)
$(POLYDATUM_WHEEL): $(shell find src -type f ! -path '*.pyc') setup.py build-requirements.txt
	pip install -r build-requirements.txt
	python setup.py build


# Publish to pypi
publish: $(POLYDATUM_WHEEL)
	pip install -r build-requirements.txt
	python setup.py publish


.PHONY: test
test: $(POLYDATUM_WHEEL)
	pip install -r test-requirements.txt ./dist/$(POLYDATUM_WHEEL)
	cd src/tests && py.test -v


.PHONY: clean
clean:
	rm -Rf dist build