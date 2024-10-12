 import logging
import os
import time
from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from square.client import Client

app = Flask(__name__)

# Set up logging
log_file_path = 'bot_activity.log'
logging.basicConfig(filename=log_file_path, level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger()

# Add log handler for console output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
logger.addHandler(console_handler)

# Set up Square client (assuming you are using real keys here)
square_client = Client(
    access_token=os.getenv('SQUARE_ACCESS_TOKEN'),
    environment='production',  # Make sure to switch to production for real payments
)

# Set up Chrome for Selenium
def setup_chrome():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    chrome_driver_path = "/usr/local/bin/chromedriver"
    return webdriver.Chrome(service=Service(chrome_driver_path), options=chrome_options)

# Function to simulate scraping and checking credit cards
def process_cards(cards_file):
    with open(cards_file, 'r') as file:
        cards = file.readlines()
    
    for card in cards:
        card = card.strip()
        if not card:
            continue

        logger.info(f"Processing card: {card}")
        try:
            # Here you would insert the logic to make a payment
            payment_response = make_payment(card)
            
            if payment_response.is_success():
                logger.info(f"Payment successful for card {card}. Sending to channel.")
                send_to_channel(card)
            else:
                logger.info(f"Payment failed for card {card}. Skipping.")
        except Exception as e:
            logger.error(f"Error processing card {card}: {e}")

# Simulate making a payment using Square API
def make_payment(card):
    # Here you should replace this with actual Square payment processing logic
    logger.info(f"Attempting to make payment with card: {card}")
    # Fake success/failure for testing:
    return FakePaymentResponse(success=True)

# Send card details to a Telegram channel (just a placeholder for now)
def send_to_channel(card):
    logger.info(f"Sending card {card} to channel...")

# Fake payment response for simulation (replace this with real API calls)
class FakePaymentResponse:
    def __init__(self, success):
        self.success = success

    def is_success(self):
        return self.success

@app.route('/logs')
def get_logs():
    """Endpoint to serve logs to the web"""
    with open(log_file_path, 'r') as file:
        logs = file.readlines()
    return jsonify({'logs': logs})

if __name__ == '__main__':
    logger.info("Bot started")
    
    # Here you would set the path to your cards.txt file
    process_cards('cards.txt')

    logger.info("Bot finished processing")

    # Running a Flask web app to serve logs
    app.run(host='0.0.0.0', port=10000)
