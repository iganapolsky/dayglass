#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/Users/iganapolsky/workspace/projects/dayglass"
APP_DIR="/Applications/Dayglass.app"
BIN_NAME="Dayglass"

echo "=== Building Dayglass.app Native macOS Bundle ==="

# 1. Compile Swift Native App
echo "[1/5] Compiling native Swift binary..."
swiftc -O -framework Cocoa -framework WebKit \
  "${REPO_DIR}/macos/main.swift" \
  -o "/tmp/${BIN_NAME}"

# 2. Setup Application Bundle Structure
echo "[2/5] Creating /Applications/Dayglass.app bundle..."
rm -rf "${APP_DIR}"
mkdir -p "${APP_DIR}/Contents/MacOS"
mkdir -p "${APP_DIR}/Contents/Resources"

# 3. Copy Executable, Info.plist, and Icon
echo "[3/5] Installing binary and bundle metadata..."
mv "/tmp/${BIN_NAME}" "${APP_DIR}/Contents/MacOS/${BIN_NAME}"
chmod +x "${APP_DIR}/Contents/MacOS/${BIN_NAME}"
cp "${REPO_DIR}/macos/Info.plist" "${APP_DIR}/Contents/Info.plist"
cp "${REPO_DIR}/macos/AppIcon.icns" "${APP_DIR}/Contents/Resources/AppIcon.icns"

# 4. Ad-hoc code sign for macOS Gatekeeper
echo "[4/5] Code-signing Dayglass.app..."
codesign --force --deep --sign - "${APP_DIR}"

# 5. Register with macOS LaunchServices
echo "[5/5] Registering with macOS LaunchServices..."
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "${APP_DIR}" 2>/dev/null || true
touch "${APP_DIR}"

echo "=== Dayglass.app successfully installed to /Applications/Dayglass.app ==="
