#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Error handling
set -e
trap 'echo -e "${RED}Error occurred. Exiting.${NC}"; exit 1' ERR

# Check root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}Please run as root (sudo)${NC}"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for main Python file
if [[ ! -f "Hyprtab.py" ]]; then
    echo -e "${RED}Hyprtab.py not found in current directory${NC}"
    exit 1
fi

# Install system dependencies
echo -e "${GREEN}Installing system dependencies...${NC}"
pacman -S --needed --noconfirm \
    python \
    python-pip \
    python-virtualenv \
    qt6-base

# Setup Python environment
echo -e "${GREEN}Setting up Python environment...${NC}"
rm -rf venv/
python -m venv venv
source venv/bin/activate

# Install Python packages
echo -e "${GREEN}Installing Python packages...${NC}"
pip install --upgrade pip
pip install pyside6 nuitka

# Verify file exists and permissions
FILE_TO_BUILD="${SCRIPT_DIR}/Hyprtab.py"
echo -e "${GREEN}Verifying file: ${FILE_TO_BUILD}${NC}"
if [[ ! -f "$FILE_TO_BUILD" ]]; then
    echo -e "${RED}Error: ${FILE_TO_BUILD} not found${NC}"
    exit 1
fi

# Build application
echo -e "${GREEN}Building application...${NC}"
PYTHONPATH="${SCRIPT_DIR}" python -m nuitka \
    --standalone \
    --onefile \
    --enable-plugin=pyside6 \
    --follow-imports \
    --output-dir="$SCRIPT_DIR/build" \
    --verbose \
    "$FILE_TO_BUILD"


# Check build output
BUILD_OUTPUT="$SCRIPT_DIR/build/Hyprtab.bin"
if [[ ! -f "$BUILD_OUTPUT" ]]; then
    echo -e "${RED}Build failed - output file not found${NC}"
    exit 1
fi
# Install
echo -e "${GREEN}Installing...${NC}"
if [[ -f "Hyprtab.bin" ]]; then
    install -Dm755 Hyprtab.bin /usr/local/bin/hyprtab
    echo -e "${GREEN}Installation complete!${NC}"
    echo "Add to Hyprland config: bind = ALT, Tab, exec, hyprtab"
else
    echo -e "${RED}Build failed - Hyprtab.bin not found${NC}"
    exit 1
fi

# Cleanup
rm -rf venv/ build/ *.spec