#!/bin/bash

# Function to check if a variable is a number (including doubles)
is_number() {
    # Use regular expression to match the number pattern
    if [[ $1 =~ ^[+-]?[0-9]+([.][0-9]+)?$ ]]; then
        return 0 # Return success (0) if it's a number
    else
        return 1 # Return failure (non-zero) if it's not a number
    fi
}

# Example usage:
variable="0.6"

is_number 0.6

if is_number "$variable"; then
    echo "$variable is a number."
else
    echo "$variable is NOT a number."
fi
