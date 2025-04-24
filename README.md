# Excalibur-V1.0

EXCALIBUR v2.0 – AI Trading Microsecond Engine  
Développé par **AVHIRAL 2025 (c)** – Projet confidentiel

------------------------------------------------------------
COMMANDES DISPONIBLES :

python3 excalibur.py --start         
    ➤ Démarre le bot en arrière-plan (fork & daemon)

python3 excalibur.py --status        
    ➤ Vérifie si le bot Excalibur est actif ou inactif

python3 excalibur.py --monitor       
    ➤ Affiche les derniers logs d’activité du bot

python3 excalibur.py --monitorlive   
    ➤ Affiche les logs en direct (mode tail -f)

python3 excalibur.py --stop          
    ➤ Arrête le bot proprement et sécurise l’état

python3 excalibur.py --report        
    ➤ Affiche les rapports de trades (latence, gains, paires)

python3 excalibur.py --web           
    ➤ Lance l'interface web sur http://IP SERVEUR LOCAL:5900

------------------------------------------------------------
TECHNIQUE :

✔ Trading haute fréquence Binance Spot (BTC/USDT, ETH/USDT, BNB/USDT)  
✔ Analyse RSI, MACD, EMA, Bandes de Bollinger  
✔ Mesure de latence en microsecondes  
✔ Génération de rapport dans excalibur_report.json  
✔ Interface web FastAPI REST + console CLI SSH

------------------------------------------------------------
INSTALLATION :

chmod +x setup.sh
./setup.sh

------------------------------------------------------------
CONFIGURATION :

1. Éditez le fichier excalibur.py
2. Remplacez :
   API_KEY = 'VOTRE_API_KEY_BINANCE'  
   API_SECRET = 'VOTRE_API_SECRET_BINANCE'  
3. Démarrez le bot avec : `python3 excalibur.py --start`  
4. Dashboard web (facultatif) : `python3 excalibur.py --web`

------------------------------------------------------------
© AVHIRAL 2025 – Tous droits réservés ⚔

DON PAYPAL : https://www.paypal.com/donate/?hosted_button_id=EZW7NMLW8YG4W
