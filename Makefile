# predatorctl — development shortcuts. `make help` lists the targets.

.PHONY: help run test install uninstall linuwu clean

help:  ## List available commands
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

run:  ## Run the app from source (dev; every write asks for a password)
	python3 src/main.py

test:  ## Run the test suite (no hardware, no GTK)
	python3 -m unittest discover tests -v

install:  ## Install system-wide (needs root: sudo make install)
	./install.sh

uninstall:  ## Remove everything install created (sudo make uninstall)
	./uninstall.sh

linuwu:  ## Install the linuwu_sense module via DKMS (optional; sudo make linuwu [LINUWU_SRC=dir])
	./install-linuwu-dkms.sh $(LINUWU_SRC)

clean:  ## Remove Python caches
	find . -type d -name "__pycache__" -exec rm -rf {} +
