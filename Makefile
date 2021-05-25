# Always fail shell on all errors
SHELL := /bin/bash -euo pipefail

# BEGIN Disable in-built Makefile rules
MAKEFLAGS += --no-builtin-rules
.SUFFIXES:
# END Disable in-built Makefile rules

IMAGE_REPO=plynth/polydatum
IMAGE_NAME=$(IMAGE_REPO):latest

%.docker-target:
	docker build -t "$(IMAGE_NAME)-$(basename $(@))" --target $(basename $(@)) .

%.shell: %.docker-target
	docker run -it --rm \
		-v "$$PWD:$$PWD" \
		-w "$$PWD" \
		--entrypoint /bin/bash \
		"$(IMAGE_NAME)-$(basename $(@))"


.PHONY: format
format: dependencies.docker-target
	docker run --rm -it \
		-v "$$PWD:$$PWD" \
		-w "$$PWD" \
		"$(IMAGE_NAME)-dependencies" \
		poe format

.PHONY: lint
lint: dependencies.docker-target
	docker run --rm -it \
		-v "$$PWD:$$PWD" \
		-w "$$PWD" \
		"$(IMAGE_NAME)-dependencies" \
		poe lint

.PHONY: test
test: dependencies.docker-target
	docker run --rm -it \
		-v "$$PWD:$$PWD" \
		-w "$$PWD" \
		"$(IMAGE_NAME)-dependencies" \
		poe test

.PHONY: readme
readme: dependencies.docker-target
	docker run --rm -it \
		-v "$$PWD:$$PWD" \
		-w "$$PWD" \
		"$(IMAGE_NAME)-dependencies" \
		rst_include include ./_README.rst ./README.rst

# Publish to pypi
publish: poetry.docker-target

.PHONY: clean
clean:
	rm -Rf dist build