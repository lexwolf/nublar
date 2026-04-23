CXX ?= g++
LDFLAGS ?=
CXXFLAGS ?= -O2 -Wall -std=c++17

# Absolute path to nano_geo_matrix subsystem
NGM_ROOT := $(realpath extern/nano_geo_matrix)
NGM_INC := $(NGM_ROOT)/include
NGM_CUP := $(NGM_ROOT)/modules/cup

BIN_DIR := bin
SRC_DIR := src
INC_DIR := include
HEADER_DIR := header
DATA_DIR := data
SCRIPT_DIR := scripts
CXXFLAGS += -I$(HEADER_DIR) -I$(INC_DIR) -I$(NGM_INC) -I$(NGM_CUP) -I/usr/include/eigen3

CORE_TARGETS := $(BIN_DIR)/transmittance $(BIN_DIR)/test_bruggeman

.PHONY: all clean dirs

all: dirs $(CORE_TARGETS)

dirs:
	mkdir -p $(BIN_DIR)

$(BIN_DIR)/transmittance: $(SRC_DIR)/transmittance.cxx extern/nano_geo_matrix/modules/cup/cup.hpp extern/nano_geo_matrix/include/nano_geo_matrix/bessel/myBessel.hpp
	$(CXX) $(CXXFLAGS) -L/usr/local/lib $< -o $@ -lgsl -lcomplex_bessel -larmadillo $(LDFLAGS)

$(BIN_DIR)/test_bruggeman: tests/test_bruggeman.cxx extern/nano_geo_matrix/modules/cup/cup.hpp extern/nano_geo_matrix/include/nano_geo_matrix/bessel/myBessel.hpp
	$(CXX) $(CXXFLAGS) -L/usr/local/lib $< -o $@ -lgsl -lcomplex_bessel -larmadillo $(LDFLAGS)

clean:
	rm -f $(CORE_TARGETS)
