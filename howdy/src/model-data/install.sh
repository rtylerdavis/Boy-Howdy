#!/bin/bash

echo "Downloading face detection and recognition models..."
echo "  YuNet (face detection, ~227 KB)"
echo "  SFace (face recognition, ~37 MB)"
echo ""

YUNET_URL="https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx"
SFACE_URL="https://huggingface.co/opencv/face_recognition_sface/resolve/main/face_recognition_sface_2021dec.onnx"

YUNET_SHA256="8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
SFACE_SHA256="0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79"

download_file() {
    local url="$1"
    local output="$2"

    if hash wget 2>/dev/null; then
        wget --help | grep -q "\--show-progress" && \
            _PROGRESS_OPT="-q --show-progress" || _PROGRESS_OPT=""
        wget $_PROGRESS_OPT --tries 5 -O "$output" "$url"
    elif hash curl 2>/dev/null; then
        curl --location --retry 5 --output "$output" "$url"
    else
        echo "Error: wget or curl is required to download model files"
        exit 1
    fi
}

verify_file() {
    local file="$1"
    local expected="$2"

    if hash sha256sum 2>/dev/null; then
        actual=$(sha256sum "$file" | cut -d' ' -f1)
    elif hash shasum 2>/dev/null; then
        actual=$(shasum -a 256 "$file" | cut -d' ' -f1)
    else
        echo "Warning: cannot verify checksum (sha256sum/shasum not found)"
        return 0
    fi

    if [ "$actual" != "$expected" ]; then
        echo "ERROR: Checksum mismatch for $file"
        echo "  Expected: $expected"
        echo "  Got:      $actual"
        rm -f "$file"
        return 1
    fi
    return 0
}

# Download YuNet
echo "Downloading YuNet face detector..."
download_file "$YUNET_URL" "face_detection_yunet_2023mar.onnx"
verify_file "face_detection_yunet_2023mar.onnx" "$YUNET_SHA256" || exit 1

# Download SFace
echo ""
echo "Downloading SFace face recognizer..."
download_file "$SFACE_URL" "face_recognition_sface_2021dec.onnx"
verify_file "face_recognition_sface_2021dec.onnx" "$SFACE_SHA256" || exit 1

# Set restrictive permissions on model files
chmod 644 face_detection_yunet_2023mar.onnx
chmod 644 face_recognition_sface_2021dec.onnx

echo ""
echo "Done! Model files downloaded and verified."
