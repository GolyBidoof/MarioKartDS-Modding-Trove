# Mario Kart DS Modding Trove
# debug/Makefile — compile-check the generic server and host example
# SPDX-License-Identifier: MIT

CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -O2
CPPFLAGS += -Iinclude -Iexamples
THREAD_FLAGS ?= -pthread
BUILD ?= build

OBJECTS = $(BUILD)/dbg_server.o $(BUILD)/bmp.o $(BUILD)/host_example.o

.PHONY: all check clean

all: $(OBJECTS)

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/dbg_server.o: src/dbg_server.c include/dbg_host.h include/dbg_server.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(THREAD_FLAGS) -c $< -o $@

$(BUILD)/bmp.o: examples/bmp.c examples/bmp.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(BUILD)/host_example.o: examples/host_example.c examples/bmp.h include/dbg_host.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

check: all

clean:
	rm -rf $(BUILD)
