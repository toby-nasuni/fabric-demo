#!/bin/bash

set -e

function deploy_s3_artifact {

    if [ -z ${1+x} ]; then
        echo "Please provide the S3 artifact to deploy"
        return 1
    fi

    local S3_ARTIFACT="$1"
    local WORKING_DIR="$HOME/tmp"
    local TARGET_DIR="$HOME/app"
    if [[ ! -d "$WORKING_DIR" ]]; then
       mkdir "$WORKING_DIR" 
    fi

    echo "Downloading Artifact"
    aws s3 cp "$S3_ARTIFACT" "$WORKING_DIR"

    if [[ ! -d "$TARGET_DIR" ]]; then
      local epoc=$(date +%s)
      BACKUP_FILE="/tmp/$epoc.tgz"
      echo "Creating backup in $BACKUP_FILE"
      tar -czf "$BACKUP_FILE" "$TARGET_DIR"
    fi

    local tarball=$(basename "$S3_ARTIFACT")
    tar -xzf "$WORKING_DIR/$tarball" -C "$WORKING_DIR"

    echo "Stopping Flask"
    sudo systemctl stop flask.service

    echo "Moving files into place"
    rm -rf "$TARGET_DIR"
    mv "$WORKING_DIR" "$TARGET_DIR"

    echo "Starting Flask"
    sudo systemctl start flask.service
}

deploy_s3_artifact $1
