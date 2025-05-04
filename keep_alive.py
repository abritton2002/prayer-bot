# keep_alive.py
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "PrayerBot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def start():
    Thread(target=run).start()
