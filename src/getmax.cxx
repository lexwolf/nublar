#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <limits>
#include <cctype>

/*
Example compilation:

g++ -std=c++17 \
  -I../include \
  -I"$(realpath ../extern/nano_geo_matrix/include)" \
  -I"$(realpath ../extern/nano_geo_matrix/modules/cup)" \
  getmax.cxx -o ../bin/getmax
*/

// Helper: check if a string is numeric
bool is_numeric(const std::string &s) {
    if (s.empty()) return false;
    char* endptr = nullptr;
    std::strtod(s.c_str(), &endptr);
    return (*endptr == '\0');
}

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

        // Skip header lines starting with # or %
        if (line[0] == '#' || line[0] == '%') continue;

        std::istringstream iss(line);
        std::vector<std::string> tokens;
        std::string tok;
        while (iss >> tok) {
            tokens.push_back(tok);
        }
        if ((int)tokens.size() < target_col) continue;

        // Check that the target column is numeric
        if (!is_numeric(tokens[0]) || !is_numeric(tokens[target_col-1])) continue;

        double x_val = std::stod(tokens[0]);
        double y_val = std::stod(tokens[target_col-1]);

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
