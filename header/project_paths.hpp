#pragma once

#include <filesystem>
#include <string>
#include <system_error>

namespace nublar {

inline std::string resolve_project_root(const char* argv0) {
    std::error_code ec;
    const std::filesystem::path exec_path = std::filesystem::weakly_canonical(
        std::filesystem::absolute(argv0), ec);

    if (!ec && exec_path.has_parent_path()) {
        return exec_path.parent_path().parent_path().string();
    }

    return ".";
}

inline std::string set_current_path_to_project_root(const char* argv0) {
    std::error_code ec;
    const std::string project_root = resolve_project_root(argv0);
    std::filesystem::current_path(project_root, ec);
    return project_root;
}

}  // namespace nublar
