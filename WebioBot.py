from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from bs4 import BeautifulSoup
from goose3 import Goose
import csv
import os
import PyPDF2
from io import BytesIO

# Constants
TOKEN: Final = "7205509402:AAFBQSuxWjuNPF-j0uKAZEg60vcSmu4mU2Y"
BOT_USERNAME: Final = "@EchoSift"
CSV_FILE: Final = "message_logs.csv"

# Initialize CSV file with headers if it doesn't exist
if not os.path.isfile(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['User ID', 'Message Type', 'Message Text'])

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Thanks for using WebioBot! How can I help you?")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("This bot can scrape websites and extract text from PDFs.")

async def input_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Please paste the link of the website from which data is to be scraped. "
        "Disclaimer: Do not paste links from .gov, .org, or any organizational or government websites."
    )

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
        await update.message.reply_text("Message deleted successfully!")
    except Exception as e:
        await update.message.reply_text(f"Failed to delete message: {str(e)}")

def handle_response(text: str) -> str:
    text = text.lower()
    if 'hello' in text:
        return 'Hey there!'
    if 'how are you' in text:
        return 'I am good!'
    if 'bye' in text:
        return "Sayonara"
    return 'I do not understand what you are trying to do...'

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text
    user_id: int = update.message.from_user.id

    print(f'User ({user_id}) in {message_type}: "{text}"')
    log_message_to_csv(user_id, message_type, text)

    if message_type == 'group':
        if BOT_USERNAME in text:
            new_text: str = text.replace(BOT_USERNAME, '').strip()
            response: str = handle_response(new_text)
        else:
            return
    else:
        if text.startswith("http://") or text.startswith("https://"):
            response: str = scrape_website(text)
        else:
            response: str = handle_response(text)

    print('Bot:', response)
    await send_long_message(update, response)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles PDF document uploads and extracts text from them."""
    document = update.message.document
    file = await document.get_file()
    file_stream = BytesIO()
    await file.download(out=file_stream)
    file_stream.seek(0)

    # Extract text from PDF
    text = extract_text_from_pdf(file_stream)
    await send_long_message(update, text)

def extract_text_from_pdf(file_stream: BytesIO) -> str:
    """Extracts text from a PDF file."""
    text = ""
    try:
        reader = PyPDF2.PdfReader(file_stream)
        for page in reader.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                text += extracted_text
    except PyPDF2.PdfReaderError as e:
        return f"Error reading PDF: {str(e)}"
    except Exception as e:
        return f"Error extracting text from PDF: {str(e)}"
    
    return text if text else "No text found in the PDF."

async def send_long_message(update: Update, response: str):
    max_length = 4096
    if len(response) > max_length:
        for i in range(0, len(response), max_length):
            await update.message.reply_text(response[i:i + max_length])
    else:
        await update.message.reply_text(response)

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')

def scrape_website(url: str) -> str:
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

        return f"Title: {title}\n\nContent:\n{body or 'No text found on the page.'}"

    except requests.exceptions.RequestException as req_err:
        return f"Network error: {req_err}"
    except Exception as e:
        return f"An error occurred while scraping: {str(e)}"

def log_message_to_csv(user_id: int, message_type: str, message_text: str):
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

    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Errors
    app.add_error_handler(error)

    # Polls the bot
    print('Polling...')
    app.run_polling(poll_interval=3)
