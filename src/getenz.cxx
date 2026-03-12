#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <limits>
#include <cmath>

/*
g++ -std=c++17 -I../include -I../extern/nano_geo_matrix/include getenz.cxx -o ../bin/getenz
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

    std::string line;
    double prev_x = 0.0, prev_y = 0.0;
    bool prev_valid = false;

    std::vector<double> enz_positions;

    while (std::getline(infile, line)) {
        if (line.empty()) continue;
        if (line[0] == '#' || line[0] == '%') continue;

        std::istringstream iss(line);
        std::vector<std::string> tokens;
        std::string tok;
        while (iss >> tok) tokens.push_back(tok);
        if ((int)tokens.size() < target_col) continue;

        if (!is_numeric(tokens[0]) || !is_numeric(tokens[target_col-1])) continue;

        double x_val = std::stod(tokens[0]);
        double y_val = std::stod(tokens[target_col-1]);

        if (prev_valid) {
            // Check for a sign change across [prev_y, y_val]
            if ((prev_y <= 0 && y_val >= 0) || (prev_y >= 0 && y_val <= 0)) {
                // Linear interpolation
                double slope = (y_val - prev_y) / (x_val - prev_x);
                if (std::fabs(slope) > 1e-12) {
                    double x_zero = prev_x - prev_y / slope;
                    enz_positions.push_back(x_zero);
                } else {
                    enz_positions.push_back(x_val); // fallback if slope ~0
                }
            }
        }

        prev_x = x_val;
        prev_y = y_val;
        prev_valid = true;
    }

    infile.close();

    if (enz_positions.empty()) {
        std::cerr << "No ENZ zero-crossings found in column " << target_col
                  << " of file " << filename << std::endl;
        return 1;
    }

    // Print results: wavelength(s) where epsilon crosses zero
    for (double enz : enz_positions) {
        std::cout << enz << std::endl;
    }

    return 0;
}
