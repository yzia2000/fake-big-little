# SPDX-License-Identifier: GPL-2.0
#
# Everything is C. There is no C++ and therefore no package manager: the only
# build inputs are clang (for BPF), cc, libbpf and bpftool.

BPFTOOL   ?= bpftool
CLANG     ?= clang
CC        ?= cc
ARCH      := $(shell uname -m | sed 's/x86_64/x86/; s/aarch64/arm64/')

SRC       := src
BIN       := build
VMLINUX_H := $(SRC)/vmlinux.h

CFLAGS    ?= -O2 -g -Wall -Wextra -Wno-unused-parameter
BPF_CFLAGS := -g -O2 -target bpf -D__TARGET_ARCH_$(ARCH) -Wall \
              -Wno-compare-distinct-pointer-types -Wno-missing-declarations -I$(SRC) -mcpu=v3

LIBBPF_CFLAGS := $(shell pkg-config --cflags libbpf 2>/dev/null)
LIBBPF_LIBS   := $(shell pkg-config --libs libbpf 2>/dev/null || echo -lbpf)

TOOLS := $(BIN)/bls $(BIN)/energy $(BIN)/pinger $(BIN)/spin

.PHONY: all clean tools check-deps
all: check-deps $(TOOLS)

check-deps:
	@command -v $(CLANG)   >/dev/null || { echo "missing: clang";   exit 1; }
	@command -v $(BPFTOOL) >/dev/null || { echo "missing: bpftool (Arch: pacman -S bpf)"; exit 1; }
	@test -r /sys/kernel/btf/vmlinux || { echo "missing: kernel BTF (CONFIG_DEBUG_INFO_BTF)"; exit 1; }

$(BIN):
	@mkdir -p $(BIN)

# Generated from the *running* kernel, so the scheduler is always built against
# the sched_ext ABI it will actually be loaded into.
$(VMLINUX_H):
	$(BPFTOOL) btf dump file /sys/kernel/btf/vmlinux format c > $@

$(BIN)/bls.bpf.o: $(SRC)/bls.bpf.c $(SRC)/bls_common.h $(VMLINUX_H) | $(BIN)
	$(CLANG) $(BPF_CFLAGS) -c $< -o $@

$(BIN)/bls.skel.h: $(BIN)/bls.bpf.o
	$(BPFTOOL) gen skeleton $< name bls_bpf > $@

$(BIN)/bls: $(SRC)/bls.c $(BIN)/bls.skel.h | $(BIN)
	$(CC) $(CFLAGS) $(LIBBPF_CFLAGS) -I$(BIN) -I$(SRC) $< -o $@ $(LIBBPF_LIBS)

$(BIN)/energy: $(SRC)/energy.c | $(BIN)
	$(CC) $(CFLAGS) $< -o $@ -lm

$(BIN)/pinger: $(SRC)/pinger.c | $(BIN)
	$(CC) $(CFLAGS) $< -o $@ -lm

$(BIN)/spin: $(SRC)/spin.c | $(BIN)
	$(CC) $(CFLAGS) $< -o $@ -lpthread

clean:
	rm -rf $(BIN) $(VMLINUX_H)
