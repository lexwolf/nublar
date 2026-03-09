CXX ?= g++
CXXFLAGS ?= -O2 -Wall -std=c++17 -I$(INC_DIR)
LDFLAGS ?=

BIN_DIR := bin
SRC_DIR := src
INC_DIR := include
DATA_DIR := data
SCRIPT_DIR := scripts

CORE_TARGETS := $(BIN_DIR)/mie $(BIN_DIR)/getmax $(BIN_DIR)/getenz $(BIN_DIR)/cm
ALIASES := $(BIN_DIR)/gmax $(BIN_DIR)/genz

.PHONY: all clean dirs

all: dirs $(CORE_TARGETS) $(ALIASES)

dirs:
	mkdir -p $(BIN_DIR)

$(BIN_DIR)/mie: $(SRC_DIR)/mie.cxx $(INC_DIR)/myBessel.H
	$(CXX) $(CXXFLAGS) -L/usr/local/lib $< -o $@ -lcomplex_bessel $(LDFLAGS)

$(BIN_DIR)/getmax: $(SRC_DIR)/getmax.cxx
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDFLAGS)

$(BIN_DIR)/getenz: $(SRC_DIR)/getenz.cxx
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDFLAGS)

$(BIN_DIR)/cm: $(SRC_DIR)/clausius-mossotti.cxx $(INC_DIR)/cup_eV.H
	$(CXX) $(CXXFLAGS) $< -o $@ -lgsl $(LDFLAGS)

$(BIN_DIR)/gmax: $(BIN_DIR)/getmax
	cp -f $< $@

$(BIN_DIR)/genz: $(BIN_DIR)/getenz
	cp -f $< $@

clean:
	rm -f $(CORE_TARGETS) $(ALIASES)
