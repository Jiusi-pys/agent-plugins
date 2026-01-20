#!/bin/bash
# setup_postfix_gmail.sh - Configure Postfix to use Gmail SMTP
# Usage: ./setup_postfix_gmail.sh <sender_gmail> <app_password>

set -e

SENDER_EMAIL="$1"
APP_PASSWORD="$2"

if [[ -z "$SENDER_EMAIL" || -z "$APP_PASSWORD" ]]; then
    echo "Usage: $0 <sender_gmail> <app_password>"
    exit 1
fi

echo "=== Installing Postfix and SASL ==="
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get install -y -qq postfix libsasl2-modules mailutils

echo "=== Configuring SASL credentials ==="
sudo mkdir -p /etc/postfix/sasl
echo "[smtp.gmail.com]:587 ${SENDER_EMAIL}:${APP_PASSWORD}" | sudo tee /etc/postfix/sasl/sasl_passwd > /dev/null

# Create hash database
sudo postmap /etc/postfix/sasl/sasl_passwd

# Set secure permissions
sudo chown root:root /etc/postfix/sasl/sasl_passwd /etc/postfix/sasl/sasl_passwd.db
sudo chmod 0600 /etc/postfix/sasl/sasl_passwd /etc/postfix/sasl/sasl_passwd.db

echo "=== Configuring Postfix main.cf ==="
POSTFIX_CONF="/etc/postfix/main.cf"

# Backup original config
sudo cp "$POSTFIX_CONF" "${POSTFIX_CONF}.bak.$(date +%Y%m%d%H%M%S)"

# Configure Gmail SMTP relay
sudo postconf -e "relayhost = [smtp.gmail.com]:587"
sudo postconf -e "smtp_sasl_auth_enable = yes"
sudo postconf -e "smtp_sasl_password_maps = hash:/etc/postfix/sasl/sasl_passwd"
sudo postconf -e "smtp_sasl_security_options = noanonymous"
sudo postconf -e "smtp_tls_security_level = encrypt"
sudo postconf -e "smtp_tls_CAfile = /etc/ssl/certs/ca-certificates.crt"

# Additional recommended settings
sudo postconf -e "smtp_use_tls = yes"
sudo postconf -e "smtp_tls_session_cache_database = btree:\${data_directory}/smtp_scache"

echo "=== Restarting Postfix ==="
sudo systemctl restart postfix
sudo systemctl enable postfix

echo "=== Verifying configuration ==="
if sudo systemctl is-active --quiet postfix; then
    echo "✓ Postfix is running"
else
    echo "✗ Postfix failed to start"
    sudo systemctl status postfix
    exit 1
fi

echo "=== Postfix Gmail SMTP configuration complete ==="
echo "Sender: $SENDER_EMAIL"
echo "Relay: [smtp.gmail.com]:587"
