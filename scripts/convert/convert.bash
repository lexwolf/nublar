#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$ROOT_DIR"

# Check if the correct number of arguments is provided
if [ "$#" -ne 2 ]; then
  echo "Usage: bash $0 input_file output_file"
  exit 1
fi

# Assign arguments to variables
input_file="$1"
output_file="$2"

# Ignore the first two lines from the input file, then extract the second and fourth columns
# and write the results to the output file
tail -n +3 "$input_file" | awk '{print $2, $4}' > "$output_file"

echo "Extraction complete. The results are written to $output_file."
