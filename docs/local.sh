#!/bin/bash

# Remove existing .rst files
rm docs/source/*.rst
rm -rf docs/reference/_autosummary

# Read exclusion patterns into an array
EXCLUDE_PATTERNS=()
while IFS= read -r line; do
    EXCLUDE_PATTERNS+=("$line")
done < <(python docs/parse_exclusions.py docs/exclusion_patterns.txt)

echo "Exclude patterns:"
echo -e "${EXCLUDE_PATTERNS[@]}\n"

# Run sphinx-apidoc with exclusion patterns
sphinx-apidoc --force -e -o docs/source . "${EXCLUDE_PATTERNS[@]}"

# Build the HTML documentation
make clean -C docs
make -C docs html

# Open the generated documentation index in the default web browser
open ./docs/_build/html/index.html
