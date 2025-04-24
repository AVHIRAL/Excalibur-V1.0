#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import ccxt
import time
import logging
import threading
import pandas as pd
import argparse
import os
import sys
import subprocess
import json
import datetime
import math
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
from threading import Thread

# Configuration
API_KEY = 'TON_API_KEY_BINANCE'
API_SECRET = 'TON_API_SECRET_BINANCE'
REFRESH_INTERVAL = 1  # en secondes
MIN_TRADE_AMOUNT = 10  # En USDT
MAX_POSITION_SIZE = 0.1
STATE_FILE = 'excalibur_state.txt'
LOG_FILE = 'excalibur.log'
REPORT_FILE = 'excalibur_report.json'
LOG_CLEAR_INTERVAL = 600
RSI_BUY_THRESHOLD = 40
RSI_SELL_THRESHOLD = 60
MAX_FAILED_TRADES = 3

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(message)s')

# Initialisation Binance
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'}
})
exchange.load_markets()

# Fonctions utilitaires
def read_bot_state():
    try:
        with open(STATE_FILE, 'r') as f:
            return f.read() == 'True'
    except FileNotFoundError:
        return False

def write_bot_state(state):
    with open(STATE_FILE, 'w') as f:
        f.write(str(state))

def clear_log_periodically():
    while True:
        time.sleep(LOG_CLEAR_INTERVAL)
        with open(LOG_FILE, 'w') as f:
            f.truncate(0)
        logging.info("Bot logs cleared.")

def log_trade(report):
    try:
        with open(REPORT_FILE, 'a') as f:
            f.write(json.dumps(report) + "\n")
    except Exception as e:
        logging.error(f"Failed to write trade report: {e}")

# Classe Excalibur v2.0
class Excalibur:
    def __init__(self):
        self.rsi_buy_threshold = RSI_BUY_THRESHOLD
        self.rsi_sell_threshold = RSI_SELL_THRESHOLD
        self.total_gain = 0
        self.failed_trades = 0
        self.selected_pair = None
        self.crypto_pairs = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        self.balances = {}
        write_bot_state(True)
        logging.info("EXCALIBUR V2.0 LANCÉ EN ARRIÈRE PLAN")

    def get_rsi(self, closes, period=14):
        delta = closes.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def fetch_balance_and_pairs(self):
        try:
            balance = exchange.fetch_balance()
            self.balances = {k: v for k, v in balance['total'].items() if v > 0}
        except Exception as e:
            logging.error(f"Balance fetch failed: {e}")

    def evaluate_pair(self, pair):
        try:
            df = pd.DataFrame(exchange.fetch_ohlcv(pair, '1h'), columns=['ts','open','high','low','close','volume'])
            if len(df) < 30:
                return float('-inf')
            df['MA30'] = df['close'].rolling(30).mean()
            df['rsi'] = self.get_rsi(df['close'])
            df['EMA12'] = df['close'].ewm(span=12).mean()
            df['EMA26'] = df['close'].ewm(span=26).mean()
            df['MACD'] = df['EMA12'] - df['EMA26']
            df['Signal'] = df['MACD'].ewm(span=9).mean()
            df['MA20'] = df['close'].rolling(20).mean()
            df['STDDEV'] = df['close'].rolling(20).std()
            df['UpperBand'] = df['MA20'] + 2 * df['STDDEV']
            df['LowerBand'] = df['MA20'] - 2 * df['STDDEV']

            score = 0
            if df['close'].iloc[-1] > df['MA30'].iloc[-1] and df['rsi'].iloc[-1] < self.rsi_buy_threshold:
                score += 2
            if df['close'].iloc[-1] < df['MA30'].iloc[-1] and df['rsi'].iloc[-1] > self.rsi_sell_threshold:
                score += 2
            if df['close'].iloc[-1] < df['LowerBand'].iloc[-1]:
                score += 1
            if df['close'].iloc[-1] > df['UpperBand'].iloc[-1]:
                score -= 1
            if df['MACD'].iloc[-1] > df['Signal'].iloc[-1]:
                score += 1
            elif df['MACD'].iloc[-1] < df['Signal'].iloc[-1]:
                score -= 1

            return score
        except Exception as e:
            logging.error(f"Erreur d'analyse pour {pair}: {e}")
            return float('-inf')

    def select_best_pair(self):
        best_score = float('-inf')
        for pair in self.crypto_pairs:
            score = self.evaluate_pair(pair)
            if score > best_score:
                best_score = score
                self.selected_pair = pair
        logging.info(f"Meilleure paire sélectionnée : {self.selected_pair}")

    def adjust_rsi_thresholds(self):
        if self.failed_trades > 0:
            self.rsi_buy_threshold = max(20, RSI_BUY_THRESHOLD - self.failed_trades * 2)
            self.rsi_sell_threshold = min(80, RSI_SELL_THRESHOLD + self.failed_trades * 2)
        else:
            self.rsi_buy_threshold = RSI_BUY_THRESHOLD
            self.rsi_sell_threshold = RSI_SELL_THRESHOLD
        logging.info(f"Seuils RSI ajustés : Buy={self.rsi_buy_threshold}, Sell={self.rsi_sell_threshold}")

    def place_order(self, side, pair, amount):
        try:
            start = time.perf_counter()
            if side == 'buy':
                order = exchange.create_market_buy_order(pair, amount)
            else:
                order = exchange.create_market_sell_order(pair, amount)
            latency = (time.perf_counter() - start) * 1e6
            logging.info(f"Ordre {side.upper()} exécuté sur {pair} avec latence {latency:.2f} µs")
            return order, latency
        except Exception as e:
            logging.error(f"Échec de l'ordre {side} sur {pair} : {e}")
            self.failed_trades += 1
            return None, 0

    def calculate_gain(self, order, amount, side):
        try:
            price = order.get('price', 0)
            gain = amount * price if side == 'sell' else -amount * price
            self.total_gain += gain
            return gain
        except Exception as e:
            logging.error(f"Erreur calcul gain: {e}")
            return 0

    def run(self):
        while read_bot_state():
            self.fetch_balance_and_pairs()
            self.select_best_pair()
            self.adjust_rsi_thresholds()
            pair = self.selected_pair
            if not pair:
                time.sleep(REFRESH_INTERVAL)
                continue

            df = pd.DataFrame(exchange.fetch_ohlcv(pair, '1h'), columns=['ts','open','high','low','close','volume'])
            df['rsi'] = self.get_rsi(df['close'])
            price = df['close'].iloc[-1]
            rsi = df['rsi'].iloc[-1]
            base_currency = pair.split('/')[0]
            available = self.balances.get(base_currency, 0)

            position_size_factor = min(max(math.log(max(self.total_gain + 1, 1)), 1), 10)
            adjusted_max_position_size = MAX_POSITION_SIZE * position_size_factor

            if price > df['close'].rolling(30).mean().iloc[-1] and rsi < self.rsi_buy_threshold and available >= MIN_TRADE_AMOUNT:
                amount = min(available * adjusted_max_position_size, available)
                order, latency = self.place_order('buy', pair, amount)
                if order:
                    gain = self.calculate_gain(order, amount, 'buy')
                    log_trade({'time': datetime.datetime.utcnow().isoformat(), 'side': 'buy', 'pair': pair, 'amount': amount, 'price': price, 'gain': gain, 'latency': latency})

            elif price < df['close'].rolling(30).mean().iloc[-1] and rsi > self.rsi_sell_threshold and available * price >= MIN_TRADE_AMOUNT:
                amount = available
                order, latency = self.place_order('sell', pair, amount)
                if order:
                    gain = self.calculate_gain(order, amount, 'sell')
                    log_trade({'time': datetime.datetime.utcnow().isoformat(), 'side': 'sell', 'pair': pair, 'amount': amount, 'price': price, 'gain': gain, 'latency': latency})

            time.sleep(REFRESH_INTERVAL)

# Interface web FastAPI
app = FastAPI()

@app.get("/status")
def status():
    return {"active": read_bot_state()}

@app.get("/report")
def get_report():
    try:
        with open(REPORT_FILE) as f:
            lines = [json.loads(line.strip()) for line in f.readlines()]
            return JSONResponse(content=lines)
    except FileNotFoundError:
        return JSONResponse(content={"message": "Aucun rapport trouvé."})

# CLI
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', action='store_true')
    parser.add_argument('--stop', action='store_true')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--monitor', action='store_true')
    parser.add_argument('--monitorlive', action='store_true')
    parser.add_argument('--report', action='store_true')
    parser.add_argument('--web', action='store_true')
    args = parser.parse_args()

    if args.start:
        pid = os.fork()
        if pid > 0:
            print("EXCALIBUR V2.0 lancé en arrière-plan.")
            sys.exit()
        else:
            bot = Excalibur()
            t_log = threading.Thread(target=clear_log_periodically, daemon=True)
            t_log.start()
            bot.run()

    elif args.stop:
        write_bot_state(False)
        logging.info("EXCALIBUR arrêté.")
        print("Bot stoppé.")

    elif args.status:
        print("Bot actif." if read_bot_state() else "Bot inactif.")

    elif args.monitor:
        try:
            with open(LOG_FILE) as f:
                print(f.read())
        except FileNotFoundError:
            print("Fichier log introuvable.")

    elif args.monitorlive:
        try:
            subprocess.call(['tail', '-f', LOG_FILE])
        except FileNotFoundError:
            print("Fichier log introuvable.")

    elif args.report:
        try:
            with open(REPORT_FILE) as f:
                for line in f:
                    print(json.loads(line))
        except FileNotFoundError:
            print("Aucun rapport disponible.")

    elif args.web:
        def start_web():
            uvicorn.run("excalibur:app", host="0.0.0.0", port=5900, log_level="info")
        Thread(target=start_web, daemon=True).start()
        print("Dashboard disponible sur http://IP SERVEUR LOCAL:5900")
        while True:
            time.sleep(10)
