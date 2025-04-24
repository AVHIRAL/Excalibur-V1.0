#!/bin/bash

echo "🚀 Installation d'Excalibur v2.0 - AVHIRAL AI Trading Bot"

# Mise à jour du système
sudo apt update && sudo apt install -y python3-pip python3-venv

# Création de l'environnement virtuel
python3 -m venv excalibur_env
source excalibur_env/bin/activate

# Installation des dépendances
pip install --upgrade pip
pip install ccxt pandas websocket-client fastapi uvicorn

# Création du fichier d'exemple de config
echo "API_KEY = 'VOTRE_API_KEY_BINANCE'" > config_exemple.txt
echo "API_SECRET = 'VOTRE_API_SECRET_BINANCE'" >> config_exemple.txt

# Message final
echo ""
echo "✅ Installation terminée."
echo "➡️  Modifiez 'excalibur.py' avec vos clés Binance API."
echo "➡️  Lancez le bot avec : python3 excalibur.py --start"
echo "➡️  Lancez le dashboard web avec : python3 excalibur.py --web"
