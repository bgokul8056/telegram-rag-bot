import os
import sys
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from rag_system import RAGSystem
from vision_system import VisionSystem

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "your_telegram_bot_token_here":
    print("Error: Please set TELEGRAM_BOT_TOKEN in .env file.")
    sys.exit(1)

import time

# Initialize RAG and Vision
rag = None
vision = None

# Rate Limiting Dictionary (user_id -> timestamp)
COOLDOWN_SECONDS = 3
user_last_action = {}

def check_ratelimit(user_id: str) -> bool:
    """Returns True if the user is ratelimited, False otherwise."""
    current_time = time.time()
    if user_id in user_last_action:
        if current_time - user_last_action[user_id] < COOLDOWN_SECONDS:
            return True
    user_last_action[user_id] = current_time
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "Hello! I am your AI Assistant.\n"
        "I can answer questions based on my internal knowledge base and look at images.\n\n"
        "Commands:\n"
        "/ask <query> - Ask me a question.\n"
        "/image - Send an image natively or reply with this command to analyze it.\n"
        "/summarize - Summarize our recent interactions.\n"
        "/help - Show this message."
    )
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Here is how you can use me:\n"
        "/ask <query> — e.g. '/ask What is the max lunch allowance?'\n"
        "/image — Upload an image to analyze it.\n"
        "/summarize — Gives you a recap of the conversation so far.\n\n"
        "You can also just send me a text message directly!"
    )
    await update.message.reply_text(help_text)

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Please provide a query. Example: /ask What is the PTO policy?")
        return
    await respond_to_query(query, update)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    greetings = ["hi", "hello", "hey", "hola", "greetings", "start"]
    
    # If the message is a simple greeting, show the welcome message and commands
    if query.lower().strip() in greetings:
        await start(update, context)
    else:
        await respond_to_query(query, update)

async def summarize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Answers the /summarize command."""
    user_id = str(update.message.from_user.id)
    if check_ratelimit(user_id):
        await update.message.reply_text("⏳ Please wait a few seconds before asking again.")
        return

    await update.message.chat.send_action(action="typing")
    try:
        reply = rag.summarize_history(user_id)
        await update.message.reply_text(f"**Here is what we've talked about recently:**\n{reply}")
    except Exception as e:
        logger.error(f"Error summarizing: {e}")
        await update.message.reply_text("Sorry, failed to summarize our history.")

async def respond_to_query(query: str, update: Update):
    user_id = str(update.message.from_user.id)
    if check_ratelimit(user_id):
        await update.message.reply_text("⏳ Please wait a few seconds before asking again.")
        return

    await update.message.chat.send_action(action="typing")
    logger.info(f"Received query from {user_id}: {query}")
    try:
        reply = rag.ask(query, user_id=user_id)
        await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"Error serving request: {e}")
        await update.message.reply_text("Sorry, an error occurred while processing your request.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if check_ratelimit(user_id):
        await update.message.reply_text("⏳ Please wait a few seconds before sending another image.")
        return
        
    if not update.message.photo:
        await update.message.reply_text("Please upload an image!")
        return

    await update.message.chat.send_action(action="typing")
    photo_file = await update.message.photo[-1].get_file()
    
    try:
        # Securely download directly into RAM as a byte array, no disk writing!
        image_bytearray = await photo_file.download_as_bytearray()
        logger.info(f"Processing vision entirely in-memory for {user_id}...")
        
        reply = vision.describe_image_bytes(bytes(image_bytearray))
        
        # Save image interaction to history so summarize knows!
        rag.save_interaction(user_id, "user", "[Sent an Image to analyze]")
        rag.save_interaction(user_id, "assistant", reply)
        
        await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"Error Serving Vision: {e}")
        await update.message.reply_text("Sorry, an error occurred while looking at your image.")

if __name__ == '__main__':
    print("Initializing RAG & Vision Systems...")
    rag = RAGSystem()
    vision = VisionSystem()
    print("Starting Telegram Bot...")
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("summarize", summarize_command))
    app.add_handler(CommandHandler("image", handle_photo))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Bot is polling. Press Ctrl+C to stop.")
    app.run_polling()
