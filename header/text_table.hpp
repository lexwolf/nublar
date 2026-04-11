#pragma once

#include <cstdlib>
#include <optional>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace nublar {

inline bool is_numeric(const std::string& text) {
    if (text.empty()) {
        return false;
    }

    char* endptr = nullptr;
    std::strtod(text.c_str(), &endptr);
    return *endptr == '\0';
}

inline std::optional<std::pair<double, double>> parse_first_and_column(
    const std::string& line,
    int target_col) {
    if (line.empty() || target_col < 1) {
        return std::nullopt;
    }

    if (line[0] == '#' || line[0] == '%') {
        return std::nullopt;
    }

    std::istringstream iss(line);
    std::vector<std::string> tokens;
    std::string token;
    while (iss >> token) {
        tokens.push_back(token);
    }

    if (static_cast<int>(tokens.size()) < target_col) {
        return std::nullopt;
    }

    if (!is_numeric(tokens[0]) || !is_numeric(tokens[target_col - 1])) {
        return std::nullopt;
    }

    return std::make_pair(std::stod(tokens[0]), std::stod(tokens[target_col - 1]));
}

}  // namespace nublar
