#!/bin/bash

# Ensure the script is run as root (necessary for installing system-wide)
if [[ $EUID -ne 0 ]]; then
    echo "Please run this script as root (e.g., with sudo)"
    exit 1
fi

# Step 1: Install necessary system dependencies (Python, pip, etc.)
echo "Installing system dependencies..."
pacman -S --noconfirm python python-pip python-xdg

# Step 2: Create a virtual environment
echo "Creating a virtual environment..."
python -m venv myenv

# Step 3: Activate the virtual environment
echo "Activating the virtual environment..."
source myenv/bin/activate

# Step 4: Install the required dependencies within the virtual environment
echo "Installing dependencies (Nuitka and PySide6)..."
pip install nuitka PySide6

# Step 5: Compile the Python script with Nuitka
echo "Compiling the program with Nuitka..."
nuitka --standalone --onefile --enable-plugin=pyside6 tab.py

# Step 6: Check if Nuitka compiled the executable successfully
if [ ! -f dist/tab ]; then
    echo "Compilation failed. Exiting."
    exit 1
fi

# Step 7: Copy the compiled executable to /usr/local/bin
echo "Copying the compiled executable to /usr/local/bin..."
cp dist/tab /usr/local/bin/hyprtab

# Step 8: Make the executable globally accessible
echo "Setting executable permissions..."
chmod +x /usr/local/bin/hyprtab

# Step 9: Clean up the virtual environment
echo "Cleaning up the virtual environment..."
deactivate
rm -rf myenv

# Step 10: Completion message
echo "Installation complete! You can now run 'hyprtab' from anywhere."
