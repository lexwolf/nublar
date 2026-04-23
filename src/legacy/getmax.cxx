#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <limits>
#include "text_table.hpp"

/*
Example compilation:

NGM_ROOT=$(realpath ../extern/nano_geo_matrix)

g++ -std=c++17 \
  -I../header \
  -I../include \
  -I"$NGM_ROOT/include" \
  -I"$NGM_ROOT/modules/cup" \
  getmax.cxx -o ../bin/getmax
*/

int main(int argc, char* argv[]) {
    if (argc < 3) {
        std::cerr << "Usage: " << argv[0] << " <filename> <column_index>" << std::endl;
        return 1;
    }

    std::string filename = argv[1];
    int target_col = std::stoi(argv[2]); // column index (1-based)

    std::ifstream infile(filename);
    if (!infile.is_open()) {
        std::cerr << "Error: could not open file " << filename << std::endl;
        return 1;
    }

    double max_val = -std::numeric_limits<double>::infinity();
    double x_at_max = 0.0;

    std::string line;
    while (std::getline(infile, line)) {
        if (line.empty()) continue;
        const auto values = nublar::parse_first_and_column(line, target_col);
        if (!values) continue;
        const auto [x_val, y_val] = *values;

        if (y_val > max_val) {
            max_val = y_val;
            x_at_max = x_val;
        }
    }

    infile.close();

    if (max_val == -std::numeric_limits<double>::infinity()) {
        std::cerr << "No valid numeric data found in column " << target_col
                  << " of file " << filename << std::endl;
        return 1;
    }

    std::cout << x_at_max << " " << max_val << std::endl;
    return 0;
}
