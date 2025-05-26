#!/bin/bash

# This script is run on the file server

THIS_PATH="(realpath "$0")"
MANIFEST_PATH="manifest.txt"

> "$MANIFEST_PATH"

echo $THIS_PATH

find . -type f ! -name "$(basename "$0")" ! -name "$(basename "$MANIFEST_PATH")" | while read -r file; do
    FILE_PATH="${file#./}"
    FILE_HASH=$(sha256sum "$FILE_PATH" | awk '{print $1}')
    printf "%s\t%s\n" "$FILE_PATH" "$FILE_HASH" >> "$MANIFEST_PATH"
done