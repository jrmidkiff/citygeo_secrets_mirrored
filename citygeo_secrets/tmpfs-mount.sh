#!/bin/bash
# Authors: Roland MacDavid and James Midkiff
set -e

# Create and mount a tmpfs device for communicating secrets
# tmpfs is a RAM device, so theoretically if someone maliciously imaged
# the underlying filesystem, they wouldn't get whatever is in here.
# https://www.kernel.org/doc/html/latest/filesystems/tmpfs.html

MOUNT_DIR="/tmpfs-secure"
TMPFS_SIZE="10M"
current_user=$(whoami) # Do not run this script with sudo - it will fail!

# Only allow this setup to work with a user that has sudo privs.
# Keeps setup specific to higher-level user and allows us to mount the device at the end.
if sudo -l -U "$current_user" 2>&1 | grep -q "is not allowed to run sudo on"; then
    echo "User $current_user does not have sudo privileges, please run as a user that does."
    exit 1
fi

# Failsafe in case we don't get proper user with whoami for some reason
if [ $(id -u $current_user) -eq 0 ]; then
    echo "Cannot mount with a UID of 0, something's gone wrong?"
    exit 1
fi
if [ $(id -g $current_user) -eq 0 ]; then
    echo "Cannot mount with a GID of 0, something's gone wrong?"
    exit 1
fi

# Check if the directory exists
if [ ! -d "$MOUNT_DIR" ]; then
    echo "Directory $MOUNT_DIR does not exist. Creating it..."
    sudo mkdir -p "$MOUNT_DIR"
    sudo chown $current_user:$current_user $MOUNT_DIR
    sudo chmod 700 $MOUNT_DIR
    if [ $? -ne 0 ]; then
        echo "Failed to create directory $MOUNT_DIR"
        exit 1
    fi
fi

# Mount tmpfs on the specified directory
if ! grep -q "$MOUNT_DIR" /etc/fstab; then
    echo "Mounting $MOUNT_DIR with privs only for $current_user UID: $(id -u $current_user)"
    echo "tmpfs $MOUNT_DIR tmpfs size=$TMPFS_SIZE,mode=0700,uid=$(id -u $current_user),gid=$(id -g $current_user) 0 0" | sudo tee -a /etc/fstab
else
    echo 'tmpfs already in fstab.'
fi

if mount | grep -q "$MOUNT_DIR"; then
    echo "$MOUNT_DIR already mounted."
else
    sudo mount "$MOUNT_DIR"
    echo "Successfully mounted $MOUNT_DIR"
fi
