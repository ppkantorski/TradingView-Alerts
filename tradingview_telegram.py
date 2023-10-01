__author__ = "Patrick Kantorski"
__version__ = "1.0.1"
__maintainer__ = "Patrick Kantorski"
__status__ = "Development Build"

import os, sys
sys.dont_write_bytecode = True
import telegram#, emoji
from telegram.ext.updater import Updater
from telegram.update import Update
from telegram.ext.callbackcontext import CallbackContext
from telegram.ext.commandhandler import CommandHandler
from telegram.ext.messagehandler import MessageHandler
from telegram.ext.filters import Filters
from telegram.ext import CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import RetryAfter
import threading
import pprint
import time
import datetime as dt
import json

#from pymemcache.client import base
#memcache_client = base.Client(('localhost', 11211))

# Define script path
telegram_path = os.path.dirname(os.path.abspath( __file__ ))




class TradingViewAlertsTelegram(object):
    def __init__(self):
        
        self.load_config()
        
        self.bot = telegram.Bot(token=self.token)
        self.updater = Updater(token=self.token, use_context=True)
        
        self.terminate = False
        self.tell_to_start = False
    
    def load_config(self):
        # load controller configurations
        load_failed = False
        if os.path.exists(f'{telegram_path}/telegram_config.json'):
            try:
                with open(f'{telegram_path}/telegram_config.json', 'r') as f:
                    self.telegram_config = json.load(f)
                
                # Telegram settings
                self.token = self.telegram_config['token']
                self.chat_id = self.telegram_config['chat_id']
                
                if len(self.token) == 0 or len(self.chat_id) == 0:
                    load_failed = True
            except:
                load_failed = True
        else:
            load_failed = True
        
        if load_failed:
            self.telegram_config = {
                "token": "",
                "chat_id": ""
            }
            self.write_config()
            
            print("Please modify 'telegram_config.json' accordingly before running again.")
            exit()
    
    
    def notify(self, message):
        try:
            self.bot.send_message(chat_id=self.chat_id, text=message)
        except RetryAfter as e:
            # Handle rate limiting error by waiting for the suggested retry time
            wait_seconds = e.retry_after
            time.sleep(wait_seconds)
            # Retry sending the message
            self.bot.send_message(chat_id=self.chat_id, text=message)
        except Exception as e:
            # Handle other exceptions here
            print(f"Error sending message: {e}")
    
    
    def write_config(self):
        with open(f'{telegram_path}/telegram_config.json', 'w') as f:
            f.write(json.dumps(self.telegram_config, sort_keys=True, indent=4))
    
    def stop(self, update: Update, context: CallbackContext):
        self.terminate = True
        self.tell_to_start = False
        #self.notify("Stop has been toggled.")
    
    def start(self, update: Update, context: CallbackContext):
        update.message.reply_text(
            f"Welcome to the TradingView Alerts Telegram Notifier!")
        self.terminate = False
        self.tell_to_start = True
    
    
    def unknown(self, update: Update, context: CallbackContext):
        pass
        #update.message.reply_text(
        #    "Sorry '%s' is not a valid command" % update.message.text)
    
    def unknown_text(self, update: Update, context: CallbackContext):
        pass
        #update.message.reply_text(
        #    "Sorry I can't recognize you , you said '%s'" % update.message.text)
    
    
    # Start bot
    def run(self):
        self.updater.dispatcher.add_handler(MessageHandler(Filters.text, self.unknown))
        self.updater.dispatcher.add_handler(MessageHandler(
            Filters.command, self.unknown))  # Filters out unknown commands
        
        # Filters out unknown messages.
        self.updater.dispatcher.add_handler(MessageHandler(Filters.text, self.unknown_text))
        
        self.updater.start_polling()

# For making object run in background
def background_thread(target, args_list):
    args = ()
    for arg in args_list:
        args += (arg,)
    pr = threading.Thread(target=target, args=args)
    pr.daemon = True
    pr.start()
    return pr


if __name__ == '__main__':
    tradingview_telegram = TradingViewAlertsTelegram()
    tradingview_telegram.run()
