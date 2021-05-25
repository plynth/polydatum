# Always fail shell on all errors
SHELL := /bin/bash -euo pipefail

# BEGIN Disable in-built Makefile rules
MAKEFLAGS += --no-builtin-rules
.SUFFIXES:
# END Disable in-built Makefile rules

IMAGE_REPO=plynth/polydatum
IMAGE_NAME=$(IMAGE_REPO):latest

define poe
	# Run a poe command
	docker run --rm -it \
		-v "$$PWD:$$PWD" \
		-w "$$PWD" \
		"$(IMAGE_NAME)-$(1)" \
		poe $(2)
endef

%.docker-target:
	docker build -t "$(IMAGE_NAME)-$(basename $(@))" --target $(basename $(@)) .

%.shell: %.docker-target
	docker run -it --rm \
		-v "$$PWD:$$PWD" \
		-w "$$PWD" \
		--entrypoint /bin/bash \
		"$(IMAGE_NAME)-$(basename $(@))"

.PHONY: format
format: dependencies.docker-target readme
	$(call poe,dependencies,format)

.PHONY: lint
lint: dependencies.docker-target
	$(call poe,dependencies,lint)

.PHONY: test
test: venv.docker-target
	$(call poe,venv,test)

test.shell:
	docker run -it --rm \
		-v "$$PWD:$$PWD" \
		-w "$$PWD" \
		-v "$$PWD/polydatum:$$(docker run --rm --entrypoint "python" "$(IMAGE_NAME)-venv" -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")/polydatum:ro" \
		--entrypoint /bin/bash \
		"$(IMAGE_NAME)-venv"

.PHONY: readme
readme: dependencies.docker-target
	$(call poe,dependencies,readme)
