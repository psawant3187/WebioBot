from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from bs4 import BeautifulSoup
from goose3 import Goose
import csv
import os

# Constants
TOKEN: Final = "7205509402:AAFBQSuxWjuNPF-j0uKAZEg60vcSmu4mU2Y"
BOT_USERNAME: Final = "@WebioBot"
CSV_FILE: Final = "message_logs.csv"

# Initialize CSV file with headers if it doesn't exist
if not os.path.isfile(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['User ID', 'Message Type', 'Message Text'])

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responds to the /start command with a greeting message."""
    await update.message.reply_text(
        "Hello! Thanks for using WebioBot! How can I help you?"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responds to the /help command with an explanation of web scraping."""
    await update.message.reply_text(
        "WEB.io, also known as web data extraction or web harvesting, is the process of automatically collecting data from websites. This process involves the use of software tools that can extract and collect information from web pages, such as text, images, and links. The collected data can be used for a wide range of purposes, including market research, competitor analysis, and data analytics."
    )

async def input_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responds to the /input command by requesting a URL from the user."""
    await update.message.reply_text(
        "Please paste the link of the website from which data is to be scraped. Disclaimer: Do not paste links from .gov, .org, or any organizational or government websites."
    )

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deletes the message that invoked the /delete command."""
    try:
        await update.message.delete()  # Delete the command message itself
        # Optionally, send a confirmation message
        await update.message.reply_text("Message deleted successfully!")
    except Exception as e:
        await update.message.reply_text(f"Failed to delete message: {str(e)}"
    )

# Function to handle response
def handle_response(text: str) -> str:
    """Determines a response based on the input text."""
    text = text.lower()

    if 'hello' in text:
        return 'Hey there!'
    
    if 'how are you' in text:
        return 'I am good!'
    
    if 'bye' in text:
        return "Sayonara"
        exit()
    
    return 'I do not understand what you are trying to do...'

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming messages, including group and direct messages."""
    message_type: str = update.message.chat.type
    text: str = update.message.text
    user_id: int = update.message.from_user.id

    print(f'User ({user_id}) in {message_type}: "{text}"')

    # Log the message details to a CSV file
    log_message_to_csv(user_id, message_type, text)

    if message_type == 'group':
        if BOT_USERNAME in text:
            new_text: str = text.replace(BOT_USERNAME, '').strip()
            response: str = handle_response(new_text)
        else:
            return
    else:
        if text.startswith("http://") or text.startswith("https://"):
            # Process URL for web scraping
            response: str = scrape_website(text)
        else:
            response: str = handle_response(text)

    print('Bot:', response)
    
    # Handle long messages
    await send_long_message(update, response)

async def send_long_message(update: Update, response: str):
    """Sends the response in chunks if it's too long."""
    max_length = 4096
    if len(response) > max_length:
        # Split the response into chunks of max_length
        for i in range(0, len(response), max_length):
            await update.message.reply_text(response[i:i + max_length])
    else:
        await update.message.reply_text(response)

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Logs errors that occur during the bot's operation."""
    print(f'Update {update} caused error {context.error}')

def scrape_website(url: str) -> str:
    """Scrapes a website and returns the title and text of the page."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        g = Goose()
        article = g.extract(url=url)

        title = article.title or "No Title Found"
        body = article.cleaned_text
        if not body:
            paragraphs = soup.find_all("p")
            body = "\n\n".join(p.text for p in paragraphs if p.text)

        if not body:
            body = "No text found on the page."

        return f"Title: {title}\n\nContent:\n{body}"

    except requests.exceptions.RequestException as req_err:
        return f"Network error: {req_err}"
    except Exception as e:
        return f"An error occurred: {str(e)}"

def log_message_to_csv(user_id: int, message_type: str, message_text: str):
    """Logs the message details to a CSV file."""
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([user_id, message_type, message_text])

if __name__ == '__main__':
    print('Starting Webio....')
    app = Application.builder().token(TOKEN).build()

    # Commands 
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('input', input_command))
    app.add_handler(CommandHandler('delete', delete_command))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Errors
    app.add_error_handler(error)

    # Polls the bot
    print('Polling...')
    app.run_polling(poll_interval=3)