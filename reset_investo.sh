#!/bin/bash
echo "Resetting Investo to first-boot mode..."

# Remove API keys
rm -f /home/pi/Investo/.env

# Remove Wi-Fi config
sudo rm -f /etc/wpa_supplicant/wpa_supplicant.conf

echo "Done. Rebooting..."
sudo reboot
