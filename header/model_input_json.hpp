#pragma once

#include <cctype>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace nublar {

class JsonValue {
public:
    enum class Type {
        Null,
        Bool,
        Number,
        String,
        Array,
        Object,
    };

    Type type = Type::Null;
    bool bool_value = false;
    double number_value = 0.0;
    std::string string_value;
    std::vector<JsonValue> array_value;
    std::map<std::string, JsonValue> object_value;

    bool is_null() const { return type == Type::Null; }
    bool is_bool() const { return type == Type::Bool; }
    bool is_number() const { return type == Type::Number; }
    bool is_string() const { return type == Type::String; }
    bool is_array() const { return type == Type::Array; }
    bool is_object() const { return type == Type::Object; }
};

class JsonParser {
public:
    explicit JsonParser(std::string text) : text_(std::move(text)) {}

    JsonValue parse()
    {
        JsonValue value = parse_value();
        skip_ws();
        if (pos_ != text_.size()) {
            fail("Unexpected trailing content");
        }
        return value;
    }

private:
    std::string text_;
    std::size_t pos_ = 0;

    [[noreturn]] void fail(const std::string& message) const
    {
        throw std::runtime_error(
            "JSON parse error at byte " + std::to_string(pos_) + ": " + message);
    }

    void skip_ws()
    {
        while (pos_ < text_.size()
               && std::isspace(static_cast<unsigned char>(text_[pos_]))) {
            ++pos_;
        }
    }

    char peek()
    {
        skip_ws();
        return pos_ < text_.size() ? text_[pos_] : '\0';
    }

    bool consume(char expected)
    {
        skip_ws();
        if (pos_ < text_.size() && text_[pos_] == expected) {
            ++pos_;
            return true;
        }
        return false;
    }

    JsonValue parse_value()
    {
        skip_ws();
        if (pos_ >= text_.size()) {
            fail("Expected value");
        }

        const char c = text_[pos_];
        if (c == '{') {
            return parse_object();
        }
        if (c == '[') {
            return parse_array();
        }
        if (c == '"') {
            JsonValue value;
            value.type = JsonValue::Type::String;
            value.string_value = parse_string();
            return value;
        }
        if (c == '-' || std::isdigit(static_cast<unsigned char>(c))) {
            JsonValue value;
            value.type = JsonValue::Type::Number;
            value.number_value = parse_number();
            return value;
        }
        if (text_.compare(pos_, 4, "true") == 0) {
            pos_ += 4;
            JsonValue value;
            value.type = JsonValue::Type::Bool;
            value.bool_value = true;
            return value;
        }
        if (text_.compare(pos_, 5, "false") == 0) {
            pos_ += 5;
            JsonValue value;
            value.type = JsonValue::Type::Bool;
            value.bool_value = false;
            return value;
        }
        if (text_.compare(pos_, 4, "null") == 0) {
            pos_ += 4;
            return {};
        }

        fail("Expected object, array, string, number, true, false, or null");
    }

    JsonValue parse_object()
    {
        JsonValue value;
        value.type = JsonValue::Type::Object;
        if (!consume('{')) {
            fail("Expected object");
        }
        if (consume('}')) {
            return value;
        }

        while (true) {
            if (peek() != '"') {
                fail("Expected object key string");
            }
            std::string key = parse_string();
            if (!consume(':')) {
                fail("Expected ':' after object key");
            }
            value.object_value.emplace(std::move(key), parse_value());
            if (consume('}')) {
                break;
            }
            if (!consume(',')) {
                fail("Expected ',' or '}' in object");
            }
        }
        return value;
    }

    JsonValue parse_array()
    {
        JsonValue value;
        value.type = JsonValue::Type::Array;
        if (!consume('[')) {
            fail("Expected array");
        }
        if (consume(']')) {
            return value;
        }

        while (true) {
            value.array_value.push_back(parse_value());
            if (consume(']')) {
                break;
            }
            if (!consume(',')) {
                fail("Expected ',' or ']' in array");
            }
        }
        return value;
    }

    std::string parse_string()
    {
        if (!consume('"')) {
            fail("Expected string");
        }

        std::string out;
        while (pos_ < text_.size()) {
            const char c = text_[pos_++];
            if (c == '"') {
                return out;
            }
            if (c != '\\') {
                out.push_back(c);
                continue;
            }
            if (pos_ >= text_.size()) {
                fail("Unterminated escape sequence");
            }
            const char esc = text_[pos_++];
            switch (esc) {
                case '"': out.push_back('"'); break;
                case '\\': out.push_back('\\'); break;
                case '/': out.push_back('/'); break;
                case 'b': out.push_back('\b'); break;
                case 'f': out.push_back('\f'); break;
                case 'n': out.push_back('\n'); break;
                case 'r': out.push_back('\r'); break;
                case 't': out.push_back('\t'); break;
                default:
                    fail("Unsupported string escape");
            }
        }
        fail("Unterminated string");
    }

    double parse_number()
    {
        const std::size_t start = pos_;
        if (text_[pos_] == '-') {
            ++pos_;
        }
        if (pos_ >= text_.size()) {
            fail("Incomplete number");
        }
        if (text_[pos_] == '0') {
            ++pos_;
        } else if (std::isdigit(static_cast<unsigned char>(text_[pos_]))) {
            while (pos_ < text_.size()
                   && std::isdigit(static_cast<unsigned char>(text_[pos_]))) {
                ++pos_;
            }
        } else {
            fail("Invalid number");
        }

        if (pos_ < text_.size() && text_[pos_] == '.') {
            ++pos_;
            if (pos_ >= text_.size()
                || !std::isdigit(static_cast<unsigned char>(text_[pos_]))) {
                fail("Invalid number fraction");
            }
            while (pos_ < text_.size()
                   && std::isdigit(static_cast<unsigned char>(text_[pos_]))) {
                ++pos_;
            }
        }

        if (pos_ < text_.size() && (text_[pos_] == 'e' || text_[pos_] == 'E')) {
            ++pos_;
            if (pos_ < text_.size() && (text_[pos_] == '+' || text_[pos_] == '-')) {
                ++pos_;
            }
            if (pos_ >= text_.size()
                || !std::isdigit(static_cast<unsigned char>(text_[pos_]))) {
                fail("Invalid number exponent");
            }
            while (pos_ < text_.size()
                   && std::isdigit(static_cast<unsigned char>(text_[pos_]))) {
                ++pos_;
            }
        }

        return std::stod(text_.substr(start, pos_ - start));
    }
};

struct ModelJsonError : std::runtime_error {
    explicit ModelJsonError(const std::string& message) : std::runtime_error(message) {}
};

enum class JsonEffectiveMediumModel {
    MaxwellGarnett,
    Bruggeman,
    Mmgm,
};

enum class JsonEffectiveMediumGeometry {
    Spheres,
    Holes,
};

enum class JsonDistributionType {
    None,
    Lognormal,
    TwoLognormal,
};

struct JsonDistribution {
    JsonDistributionType type = JsonDistributionType::None;
    double rave_nm = 0.0;
    double mu_l = 0.0;
    double sig_l = 0.0;
    double w1 = 0.0;
    double mu_l1 = 0.0;
    double sig_l1 = 0.0;
    double w2 = 0.0;
    double mu_l2 = 0.0;
    double sig_l2 = 0.0;
};

struct JsonEffectiveMedium {
    JsonEffectiveMediumModel model = JsonEffectiveMediumModel::Mmgm;
    JsonEffectiveMediumGeometry geometry = JsonEffectiveMediumGeometry::Spheres;
    double filling_fraction = 0.0;
    std::string metal_material = "silverUNICALeV.dat";
    std::string host_material = "air";
    JsonDistribution distribution;
};

struct JsonLayer {
    std::string name;
    std::string kind;
    std::string material;
    std::string coherence = "coherent";
    double thickness_nm = 0.0;
    JsonEffectiveMedium effective_medium;
};

struct JsonWavelengthGrid {
    double min_nm = 0.0;
    double max_nm = 0.0;
    double step_nm = 0.0;
};

struct JsonStack {
    std::string incident_material;
    std::string exit_material;
    std::vector<JsonLayer> layers;
};

struct JsonOutput {
    std::string path;
};

struct TransmittanceModelJson {
    JsonWavelengthGrid wavelength_grid;
    JsonStack stack;
    JsonOutput output;
};

inline const JsonValue& require_object_field(const JsonValue& object,
                                             const std::string& field,
                                             const std::string& path)
{
    if (!object.is_object()) {
        throw ModelJsonError(path + " must be an object");
    }
    const auto it = object.object_value.find(field);
    if (it == object.object_value.end()) {
        throw ModelJsonError("Missing required JSON field: " + path + "." + field);
    }
    return it->second;
}

inline const JsonValue* optional_object_field(const JsonValue& object,
                                              const std::string& field)
{
    if (!object.is_object()) {
        return nullptr;
    }
    const auto it = object.object_value.find(field);
    return it == object.object_value.end() ? nullptr : &it->second;
}

inline std::string require_string(const JsonValue& value, const std::string& path)
{
    if (!value.is_string()) {
        throw ModelJsonError(path + " must be a string");
    }
    return value.string_value;
}

inline double require_number(const JsonValue& value, const std::string& path)
{
    if (!value.is_number() || !std::isfinite(value.number_value)) {
        throw ModelJsonError(path + " must be a finite number");
    }
    return value.number_value;
}

inline std::string optional_string(const JsonValue& object,
                                   const std::string& field,
                                   const std::string& fallback)
{
    const JsonValue* value = optional_object_field(object, field);
    return value == nullptr ? fallback : require_string(*value, field);
}

inline JsonEffectiveMediumModel parse_json_effective_medium_model(const std::string& value)
{
    if (value == "mg") {
        return JsonEffectiveMediumModel::MaxwellGarnett;
    }
    if (value == "bruggeman") {
        return JsonEffectiveMediumModel::Bruggeman;
    }
    if (value == "mmgm") {
        return JsonEffectiveMediumModel::Mmgm;
    }
    throw ModelJsonError(
        "Unsupported effective_medium.model '" + value + "'. Options are: mg, bruggeman, mmgm.");
}

inline JsonEffectiveMediumGeometry parse_json_effective_medium_geometry(const std::string& value)
{
    if (value == "spheres") {
        return JsonEffectiveMediumGeometry::Spheres;
    }
    if (value == "holes") {
        return JsonEffectiveMediumGeometry::Holes;
    }
    throw ModelJsonError(
        "Unsupported effective_medium.geometry '" + value + "'. Options are: spheres, holes.");
}

inline JsonDistribution parse_distribution(const JsonValue& object, const std::string& path)
{
    JsonDistribution distribution;
    const std::string type = require_string(require_object_field(object, "type", path), path + ".type");
    distribution.rave_nm = require_number(
        require_object_field(object, "rave_nm", path), path + ".rave_nm");
    if (distribution.rave_nm <= 0.0) {
        throw ModelJsonError(path + ".rave_nm must be positive");
    }

    if (type == "lognormal") {
        distribution.type = JsonDistributionType::Lognormal;
        distribution.mu_l = require_number(require_object_field(object, "muL", path), path + ".muL");
        distribution.sig_l = require_number(require_object_field(object, "sigL", path), path + ".sigL");
        if (distribution.sig_l <= 0.0) {
            throw ModelJsonError(path + ".sigL must be positive");
        }
        return distribution;
    }

    if (type == "two_lognormal") {
        distribution.type = JsonDistributionType::TwoLognormal;
        distribution.w1 = require_number(require_object_field(object, "w1", path), path + ".w1");
        distribution.mu_l1 = require_number(require_object_field(object, "muL1", path), path + ".muL1");
        distribution.sig_l1 = require_number(require_object_field(object, "sigL1", path), path + ".sigL1");
        distribution.w2 = require_number(require_object_field(object, "w2", path), path + ".w2");
        distribution.mu_l2 = require_number(require_object_field(object, "muL2", path), path + ".muL2");
        distribution.sig_l2 = require_number(require_object_field(object, "sigL2", path), path + ".sigL2");
        if (distribution.sig_l1 <= 0.0 || distribution.sig_l2 <= 0.0) {
            throw ModelJsonError(path + ".sigL1 and .sigL2 must be positive");
        }
        return distribution;
    }

    throw ModelJsonError(
        "Unsupported distribution.type '" + type + "'. Options are: lognormal, two_lognormal.");
}

inline JsonEffectiveMedium parse_effective_medium(const JsonValue& object, const std::string& path)
{
    JsonEffectiveMedium effective_medium;
    effective_medium.model = parse_json_effective_medium_model(require_string(
        require_object_field(object, "model", path), path + ".model"));
    effective_medium.geometry = parse_json_effective_medium_geometry(require_string(
        require_object_field(object, "geometry", path), path + ".geometry"));
    effective_medium.filling_fraction = require_number(
        require_object_field(object, "filling_fraction", path), path + ".filling_fraction");
    if (effective_medium.filling_fraction < 0.0 || effective_medium.filling_fraction > 1.0) {
        throw ModelJsonError(path + ".filling_fraction must be in [0, 1]");
    }
    effective_medium.metal_material = optional_string(object, "metal_material", "silverUNICALeV.dat");
    effective_medium.host_material = optional_string(object, "host_material", "air");

    if (effective_medium.model == JsonEffectiveMediumModel::Mmgm) {
        effective_medium.distribution = parse_distribution(
            require_object_field(object, "distribution", path), path + ".distribution");
    } else if (optional_object_field(object, "distribution") != nullptr) {
        throw ModelJsonError(path + ".distribution is only supported when model is mmgm");
    }

    return effective_medium;
}

inline JsonLayer parse_layer(const JsonValue& object, std::size_t index)
{
    const std::string path = "stack.layers[" + std::to_string(index) + "]";
    JsonLayer layer;
    layer.name = optional_string(object, "name", "layer_" + std::to_string(index));
    layer.kind = require_string(require_object_field(object, "kind", path), path + ".kind");
    layer.thickness_nm = require_number(
        require_object_field(object, "thickness_nm", path), path + ".thickness_nm");
    if (layer.thickness_nm < 0.0) {
        throw ModelJsonError(path + ".thickness_nm must be non-negative");
    }
    layer.coherence = optional_string(object, "coherence", "coherent");
    if (layer.coherence != "coherent" && layer.coherence != "incoherent") {
        throw ModelJsonError(path + ".coherence must be 'coherent' or 'incoherent'");
    }

    if (layer.kind == "effective_medium") {
        layer.effective_medium = parse_effective_medium(
            require_object_field(object, "effective_medium", path), path + ".effective_medium");
    } else if (layer.kind == "dielectric") {
        layer.material = require_string(require_object_field(object, "material", path), path + ".material");
    } else {
        throw ModelJsonError(path + ".kind must be 'effective_medium' or 'dielectric'");
    }

    return layer;
}

inline TransmittanceModelJson parse_transmittance_model_json(const JsonValue& root)
{
    if (!root.is_object()) {
        throw ModelJsonError("Top-level JSON value must be an object");
    }

    TransmittanceModelJson model;
    const JsonValue& grid = require_object_field(root, "wavelength_grid_nm", "$");
    model.wavelength_grid.min_nm = require_number(
        require_object_field(grid, "min", "wavelength_grid_nm"), "wavelength_grid_nm.min");
    model.wavelength_grid.max_nm = require_number(
        require_object_field(grid, "max", "wavelength_grid_nm"), "wavelength_grid_nm.max");
    model.wavelength_grid.step_nm = require_number(
        require_object_field(grid, "step", "wavelength_grid_nm"), "wavelength_grid_nm.step");
    if (model.wavelength_grid.step_nm <= 0.0) {
        throw ModelJsonError("wavelength_grid_nm.step must be positive");
    }
    if (model.wavelength_grid.max_nm < model.wavelength_grid.min_nm) {
        throw ModelJsonError("wavelength_grid_nm.max must be >= wavelength_grid_nm.min");
    }

    const JsonValue& stack = require_object_field(root, "stack", "$");
    const JsonValue& incident = require_object_field(stack, "incident_medium", "stack");
    const JsonValue& exit = require_object_field(stack, "exit_medium", "stack");
    model.stack.incident_material = require_string(
        require_object_field(incident, "material", "stack.incident_medium"),
        "stack.incident_medium.material");
    model.stack.exit_material = require_string(
        require_object_field(exit, "material", "stack.exit_medium"),
        "stack.exit_medium.material");

    const JsonValue& layers = require_object_field(stack, "layers", "stack");
    if (!layers.is_array() || layers.array_value.empty()) {
        throw ModelJsonError("stack.layers must be a non-empty array");
    }
    for (std::size_t i = 0; i < layers.array_value.size(); ++i) {
        model.stack.layers.push_back(parse_layer(layers.array_value[i], i));
    }

    if (const JsonValue* output = optional_object_field(root, "output")) {
        if (const JsonValue* path = optional_object_field(*output, "path")) {
            model.output.path = require_string(*path, "output.path");
        }
    }

    return model;
}

inline TransmittanceModelJson read_transmittance_model_json(const std::filesystem::path& path)
{
    std::ifstream input(path);
    if (!input.is_open()) {
        throw ModelJsonError("Could not open JSON model file: " + path.string());
    }
    std::ostringstream buffer;
    buffer << input.rdbuf();
    JsonParser parser(buffer.str());
    return parse_transmittance_model_json(parser.parse());
}

} // namespace nublar
