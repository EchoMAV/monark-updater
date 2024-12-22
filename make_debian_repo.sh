#!/bin/bash
# This script will create a debian repository for the debs for MONARK.
set -e

SUDO=$(test ${EUID} -ne 0 && which sudo)

# Install necessary packages
$SUDO apt install -y dpkg-dev gnupg apt-utils zip

DEBIAN_REPO_DIR="monark-updates"
DEBIAN_REPO_ZIP="monark-updates.zip"
BUILD_EMAIL="MONARK@ECHOMAV.COM"

# Recreate build directory
$SUDO rm -f $DEBIAN_REPO_ZIP
$SUDO rm -rf $DEBIAN_REPO_DIR
$SUDO mkdir -p $DEBIAN_REPO_DIR
$SUDO chmod 755 $DEBIAN_REPO_DIR
$SUDO chown -R echopilot:echopilot $DEBIAN_REPO_DIR

# Get each deb to add to the repo
PISTREAMER_DEB_FILE=$(find ./pistreamer -type f -name "*arm64.deb" | head -n 1)
MONARK_UPDATER_DEB_FILE=$(find ./monark-updater  -type f -name "*arm64.deb" | head -n 1)
MICROHARD_DEB_FILE=$(find ./microhard  -type f -name "*arm64.deb" | head -n 1)

# Copy the debs to the repo staging folder
$SUDO cp $PISTREAMER_DEB_FILE $DEBIAN_REPO_DIR
$SUDO cp $MONARK_UPDATER_DEB_FILE $DEBIAN_REPO_DIR
$SUDO cp $MICROHARD_DEB_FILE $DEBIAN_REPO_DIR

# Do the gpg commands
if [ ! -f private-key.asc ]; then
    echo "Error. MONARK private-key.asc not found."
    exit 1
fi

if [ -z "${PASSPHRASE}" ]; then
  echo "Error: Environment variable PASSPHRASE is not set."
  exit 1
fi

$SUDO gpg --batch --import private-key.asc
cd $DEBIAN_REPO_DIR
$SUDO dpkg-scanpackages . /dev/null | $SUDO tee Packages > /dev/null
$SUDO gzip -k -f Packages
$SUDO apt-ftparchive release . | $SUDO tee Release > /dev/null

# Retrieve the fingerprint of the key
KEY_FINGERPRINT=$(gpg --list-keys --with-colons $BUILD_EMAIL | awk -F: '/^fpr:/ {print $10; exit}')

# Sign the Release file
$SUDO gpg --default-key $KEY_FINGERPRINT --batch --pinentry-mode="loopback" --passphrase ${PASSPHRASE} -abs -o Release.gpg Release
$SUDO gpg --default-key $KEY_FINGERPRINT --batch --pinentry-mode="loopback" --passphrase ${PASSPHRASE} --clearsign -o InRelease Release

# Create a zip file of the debian repo (delete the old one first)
cd ..
$SUDO zip -r $DEBIAN_REPO_ZIP $DEBIAN_REPO_DIR
$SUDO chown -R echopilot:echopilot $DEBIAN_REPO_ZIP

echo
echo "=======-------======="
echo
echo "$DEBIAN_REPO_ZIP has been created and ready for distribution."
echo
echo "=======-------======="
