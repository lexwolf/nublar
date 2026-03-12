CXX ?= g++
LDFLAGS ?=

BIN_DIR := bin
SRC_DIR := src
INC_DIR := include
DATA_DIR := data
SCRIPT_DIR := scripts
NGM_ROOT := $(realpath extern/nano_geo_matrix)
NGM_INC := $(NGM_ROOT)/include
NGM_CUP := $(NGM_ROOT)/modules/cup

CXXFLAGS ?= -O2 -Wall -std=c++17 -I$(INC_DIR) -I$(NGM_INC) -I$(NGM_CUP) -I/usr/include/eigen3

CORE_TARGETS := $(BIN_DIR)/mie $(BIN_DIR)/getmax $(BIN_DIR)/getenz $(BIN_DIR)/cm
ALIASES := $(BIN_DIR)/gmax $(BIN_DIR)/genz

.PHONY: all clean dirs

all: dirs $(CORE_TARGETS) $(ALIASES)

dirs:
	mkdir -p $(BIN_DIR)

$(BIN_DIR)/mie: $(SRC_DIR)/mie.cxx extern/nano_geo_matrix/include/nano_geo_matrix/bessel/myBessel.hpp
	$(CXX) $(CXXFLAGS) -L/usr/local/lib $< -o $@ -lcomplex_bessel -larmadillo $(LDFLAGS)

$(BIN_DIR)/getmax: $(SRC_DIR)/getmax.cxx
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDFLAGS)

$(BIN_DIR)/getenz: $(SRC_DIR)/getenz.cxx
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDFLAGS)

$(BIN_DIR)/cm: $(SRC_DIR)/clausius-mossotti.cxx extern/nano_geo_matrix/modules/cup/cup.hpp
	$(CXX) $(CXXFLAGS) $< -o $@ -lgsl $(LDFLAGS)

$(BIN_DIR)/gmax: $(BIN_DIR)/getmax
	cp -f $< $@

$(BIN_DIR)/genz: $(BIN_DIR)/getenz
	cp -f $< $@

clean:
	rm -f $(CORE_TARGETS) $(ALIASES)
