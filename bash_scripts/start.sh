#!/bin/bash

set -x -o errexit

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get reinstall sudo -y
apt-get reinstall clamav-daemon -y

# Get latest definitions
freshclam

# Note: clamav takes the _first_ config value found in the file, so first
# remove any existing values, then append the new values.
grep -vE "^(StreamMaxLength|MaxScanSize|MaxFileSize|MaxRecursion|MaxFiles|TCPSocket|TCPAddr)" /etc/clamav/clamd.conf  > /etc/clamav/clamd.conf.new
cat >> /etc/clamav/clamd.conf.new << EOF

# This option allows you to specify the upper limit for data size that will be transfered to remote daemon when scanning a single file.
StreamMaxLength 521M

# Sets the maximum amount of data to be scanned for each input file.
# Archives and other containers are recursively extracted and scanned up to this value.
MaxScanSize 512M

# Files larger than this limit won't be scanned.
# Affects the input file itself as well as files contained inside it (when the input file is an archive, a document or some other kind of container).
MaxFileSize 512M

# Nested archives are scanned recursively, e.g. if a Zip archive contains a RAR file, all files within it will also be scanned.
# This options specifies how deeply the process should be continued.
MaxRecursion 16

# Number of files to be scanned within an archive, a document, or any other kind of container.
MaxFiles 10000

# Port and bind address for clamav daemon
TCPSocket 3310
TCPAddr 127.0.0.1

EOF

mv -f /etc/clamav/clamd.conf.new /etc/clamav/clamd.conf

# Report options to log
clamconf

# Restart Services
service clamav-daemon force-reload
service clamav-freshclam force-reload

# Run python server process
flask run
