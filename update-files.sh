#!/bin/bash

set -e

# modified from https://unix.stackexchange.com/questions/60653/urlencode-function
urlencode_od_awk () {
  echo -n "$1" | od -t d1 | awk '{
      for (i = 2; i <= NF; i++) {
        if (($i>=48 && $i<=57) ||  # 0-9
            ($i>=65 && $i<=90) ||  # A-Z
            ($i>=97 && $i<=122) || # a-z
            $i==45 || $i==46 || $i==95 || $i==126 || $i==47)  # - . _ ~ /
        {
          printf "%c", $i
        } else {
          printf "%%%02x", $i
        }
      }
    }'
}


# This isn't publicly available at the moment.
# I doubt anyone is going to be trying to download these anyway, but reach out if you want them.
FILE_SERVER_URL="https://glisterbot.glisterbyte.com"
FILE_DIR="files"

# read -p "Enter username for file server: " USERNAME
# read -p "Enter password for file server: " PASSWORD
***REMOVED***
***REMOVED***

mkdir -p "$FILE_DIR"

echo "Downloading manifest..."
curl -u $USERNAME:$PASSWORD -s -o "$FILE_DIR/manifest.txt" "$FILE_SERVER_URL/manifest.txt"

while IFS=$'\t' read -r remotepath remotehash; do
    localpath="$FILE_DIR/$remotepath"
    if [[ -f "$localpath" ]]; then
        localhash=$(sha256sum "$localpath" | awk '{print $1}')
        if [[ "$localhash" == "$remotehash" ]]; then
            echo "Skipping $remotepath"
            continue
        fi
    fi
    echo "Downloading $remotepath..."
    mkdir -p "$(dirname "$localpath")"
    encodedpath=$(urlencode_od_awk "$remotepath")
    curl -u $USERNAME:$PASSWORD -s -o "$localpath" "$FILE_SERVER_URL/$encodedpath"
done < "$FILE_DIR/manifest.txt"