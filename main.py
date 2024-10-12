import asyncio
import telebot
import os
import json
import logging
import aiofiles  # Ensure aiofiles is imported for async file handling
from square.client import Client  # Import the Square client
from flask import Flask, request, jsonify, render_template, Response  # Import Flask-related classes

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
    environment='sandbox'  # Use sandbox for testing purposes
)

# Initialize Flask app
app = Flask(__name__)

# Hardcoded Telegram Bot Token
API_TOKEN = "7785068082:AAEwD4mFUHLVLSeA5JrXZYnj8UKt52cFpHw"  # User's Telegram bot token
bot = telebot.TeleBot(API_TOKEN)

# Set the target Telegram channel
target_channel = os.getenv('TARGET_CHANNEL', '@cctalks700')  # Set in Render's environment variables

# Function to send confirmation to the target channel
def send_to_target_channel(transaction_info):
    try:
        bot.send_message(target_channel, f"Transaction Approved: {transaction_info}")
        logging.info(f"Sent to {target_channel}: Transaction Approved: {transaction_info}")
    except Exception as e:
        logging.error(f"Failed to send message: {e}")

# Function to process payment using the tokenized card nonce
async def process_payment(nonce):
    try:
        # Create a payment request to Square for $0.01 using the nonce from the front end
        body = {
            "source_id": nonce,  # Use the actual nonce received from the front end
            "amount_money": {
                "amount": 1,  # Amount in cents, $0.01
                "currency": "USD"
            },
            "idempotency_key": os.urandom(16).hex()  # Ensure each transaction is unique
        }

        result = square_client.payments.create_payment(body)

        if result.is_success:
            logging.info("Payment successful.")
            return {"status": "success", "transaction": result.body['payment']}  # Return transaction info
        else:
            logging.warning(f"Payment failed: {result.errors}")
            return {"status": "error", "errors": result.errors}

    except Exception as e:
        logging.error(f"Error processing payment: {e}")
        return {"status": "error", "error": str(e)}

# Function to read card details from cards.txt and process payments
async def scrape_and_process_payments():
    try:
        async with aiofiles.open('cards.txt', 'r') as file:
            lines = await file.readlines()

        for line in lines:
            card_details = line.strip().split('|')  # Split card details by '|'
            logging.info(f"Processing card: {card_details[0]}")  # Log the card being processed

            # Create a nonce using Square's Web Payments SDK
            nonce = "cnon:card-nonce-ok"  # Placeholder nonce for testing, replace with actual tokenization logic

            # Process the payment asynchronously
            approved_payment = await process_payment(nonce)  # Pass the nonce to process payment
            if approved_payment and approved_payment['status'] == "success":
                send_to_target_channel(approved_payment['transaction']['id'])  # Send approved transaction ID to Telegram
            else:
                logging.warning(f"Skipping card: {card_details[0]}, status: {approved_payment['status']}")

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
