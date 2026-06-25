#!/bin/bash
echo "--- Checking PO-Online Service Status ---"
sudo systemctl status po-online --no-pager

echo -e "\n--- Checking Port 8080 Listening ---"
sudo ss -tulpn | grep :8080

echo -e "\n--- Checking Firewall (UFW) ---"
sudo ufw status | grep 8080

echo -e "\n--- Recent Application Logs ---"
sudo journalctl -u po-online -n 20 --no-pager
