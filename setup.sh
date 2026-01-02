#!/bin/bash

# --- 1. System Updates & Essentials ---
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential curl git wget software-properties-common

# --- 2. Python Development Tools ---
echo "Installing Python essentials..."
sudo apt install -y python3-pip python3-venv

# --- 3. Install Miniconda ---
echo "Installing Miniconda..."
cd /tmp
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda3
# Initialize for Bash
eval "$($HOME/miniconda3/bin/conda shell.bash hook)"
conda init
# Prevent conda from activating 'base' by default
conda config --set auto_activate_base false

# --- 4. Install ROS 2 Jazzy Jalisco ---
echo "Setting up ROS 2 Jazzy..."
# Set Locale
sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# Add ROS 2 Repository
sudo add-apt-repository universe -y
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# Install ROS 2 Desktop and Dev Tools
sudo apt update
sudo apt install -y ros-jazzy-desktop ros-dev-tools

# --- 5. Install Gazebo Harmonic ---
echo "Installing Gazebo Harmonic (default for Jazzy)..."
sudo apt install -y ros-jazzy-ros-gz

# --- 6. Environment Sourcing ---
echo "Finalizing environment..."
if ! grep -q "source /opt/ros/jazzy/setup.bash" ~/.bashrc; then
    echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
fi

echo "--------------------------------------------------"
echo "SETUP COMPLETE!"
echo "Please RESTART your terminal to apply changes."
echo "Test Gazebo by running: gz sim"
echo "Test ROS 2 by running: ros2 --version"
echo "--------------------------------------------------"
