__author__ = "Patrick Kantorski"
__version__ = "1.0.3"
__maintainer__ = "Patrick Kantorski"
__status__ = "Development Build"

import os
import sys
import time
import threading
import sqlite3
import base64
import importlib
import urllib.parse
from queue import Queue
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
from pprint import pprint
import json

# Change working directory to location of script
os.chdir(os.path.dirname(os.path.realpath(__file__)))

class TradingViewAlertsHandler:
    def __init__(self):
        self.STRATEGY_COLUMNS = []
        self.CREDENTIALS_FILE = 'credentials.json'
        self.TOKEN_FILE = 'token.json'
        self.SQL_COLUMNS = ['message_id', 'msg_timestamp', 'alert']
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
        self.EMAIL_SENDER = "TradingView <noreply@tradingview.com>"
        self.N_DAYS = 10
        self.start = False
        self.kill_daemon = False
        self.initial_run = True
        self.message_queue = Queue()
        self.telegram_path = os.path.dirname(os.path.abspath(__file__))
        sys.path.append(self.telegram_path)
        tradingview_telegram_lib = importlib.import_module('tradingview_telegram')
        self.TradingViewAlertsTelegram = tradingview_telegram_lib.TradingViewAlertsTelegram
        self.tradingview_telegram = self.TradingViewAlertsTelegram()
        self.load_config() # Load alert configurations file.
    
    def load_config(self):
        # Load configuration from config.json
        with open('config.json', 'r') as config_file:
            config = json.load(config_file)

        # Access configuration values
        self.STRATEGY_COLUMNS = config["STRATEGY_COLUMNS"]
        self.CREDENTIALS_FILE = config["CREDENTIALS_FILE"]
        self.TOKEN_FILE = config["TOKEN_FILE"]
        
    def notify_command(self, message):
        self.tradingview_telegram.notify(message=message)
    
    def message_daemon(self):
        while not self.start:
            time.sleep(1)
        
        while not self.kill_daemon:
            try:
                if not self.message_queue.empty():
                    print("Sending message...")
                    message = self.message_queue.get()
                    self.notify_command(message)
                    time.sleep(2)  # Adjust the delay as needed
            except Exception as e:
                print(f"An error occurred: {e}")
                self.kill_daemon = True
    
    
    def extract_info_from_message(self, message_text):
        msg_lines = message_text.split('\n')
        msg_lines = [msg_line.strip('\r') for msg_line in msg_lines if msg_line != '\r']
    
        info = {}
        for column in self.STRATEGY_COLUMNS:
            for line in msg_lines:
                if column in line:
                    value = line.split(column)[-1].lstrip(':').strip()
                    info[column.lower()] = value
                    break
    
        # Add default values for missing keywords
        for column in self.STRATEGY_COLUMNS:
            if column.lower() not in info.keys():
                info[column.lower()] = None
    
        return info
    
    def authenticate_and_fetch_alerts(self):
        if not os.path.exists(self.TOKEN_FILE):
            flow = InstalledAppFlow.from_client_secrets_file(self.CREDENTIALS_FILE, self.SCOPES)
            creds = flow.run_local_server(port=0)
            with open(self.TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())

        # Load the token from file
        creds = Credentials.from_authorized_user_file(self.TOKEN_FILE, self.SCOPES)

        # Create a Gmail API service
        service = build('gmail', 'v1', credentials=creds)

        # Calculate the timestamp for n days ago
        n_days_ago = datetime.now() - timedelta(days=self.N_DAYS)
        
        
        # Connect to the SQLite database
        conn = sqlite3.connect('tradingview_alerts.db')
        cursor = conn.cursor()


        strategy_table_lines = [f"{column.lower()} TEXT, " for column in self.STRATEGY_COLUMNS]
        strategy_table_line = ''
        for i in range(len(strategy_table_lines)):
            line = strategy_table_lines[i]
            if 'timestamp' in line:
                line = line.replace("TEXT", "DATETIME")
            
            if i == len(strategy_table_lines)-1:
                line = line.rstrip(', ')
            
            strategy_table_line += line
        
        # Update the schema based upon the strategy columns
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS alerts (
                {self.SQL_COLUMNS[0]} TEXT PRIMARY KEY,
                {self.SQL_COLUMNS[1]} DATETIME,
                {self.SQL_COLUMNS[2]} TEXT,
                {strategy_table_line}
            )
        ''')

        conn.commit()
        
        # Initialize backoff parameters
        retries = 0
        max_retries = 5
        base_delay = 3  # Initial delay in seconds
        results = None
        
        messages = []
        while retries < max_retries:
            try:
                # Your existing code for fetching messages
                query = 'after:' + n_days_ago.strftime('%Y/%m/%d') + ' from:' + self.EMAIL_SENDER
                results = service.users().messages().list(userId='me', q='after:' + n_days_ago.strftime('%Y/%m/%d')).execute()
                messages = results.get('messages', [])
                
                break  # Break out of the loop if successful
            except Exception as e:
                print(f"Error: {str(e)}")
                retries += 1
                if retries < max_retries:
                    delay = base_delay * (2 ** retries)
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print("Max retries reached. Exiting.")
                    self.kill_daemon = True
                    break
        
        
        
        alert_found = False
        
        if len(messages) > 0:
            
            for message in messages:
                msg_id = message['id']
    
                # Check if the message timestamp is not already stored in the database
                cursor.execute('SELECT * FROM alerts WHERE message_id = ?', (msg_id,))
                if cursor.fetchone():
                    continue  # Skip if this email is already in the database
    
                msg = service.users().messages().get(userId='me', id=msg_id).execute()
                
                headers = msg['payload']['headers']
                subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')
                date = next((header['value'] for header in headers if header['name'] == 'Date'), 'No Date')
    
                # Check if the subject starts with "Alert" and if the sender is "<noreply@tradingview.com>"
                if subject.startswith("Alert"):
                    msg_data = msg['payload']['body']['data']
                    msg_data = base64.urlsafe_b64decode(msg_data.encode('ASCII')).decode('utf-8')
                    
                    alert_found = True
                    print(f'Subject: {subject}, Date: {date}\n')
                    
                    start_index = None
                    end_index = None
                    start_identifier = f'">{self.STRATEGY_COLUMNS[0]}: '
                    end_identifier = "</p>"
                    
                    start_index = msg_data.find(start_identifier)
                    msg_data = msg_data[start_index:]
                    end_index = msg_data.find(end_identifier)
                    
                    msg_data = msg_data[:end_index].strip(end_identifier).lstrip('">')
                    print(msg_data+'\n')
                    
                    
                    # Extract information from the message
                    extracted_info = self.extract_info_from_message(msg_data)
                    
                    alert = subject.replace('Alert: ', '')
                
                
                    # Insert the extracted data into the 'alerts' table
                    columns_line = ', '.join(self.SQL_COLUMNS + [column.lower() for column in self.STRATEGY_COLUMNS])
                    insertion_line = ', '.join(['?']*(len(self.SQL_COLUMNS) + len(self.STRATEGY_COLUMNS)))
                    
                    # Define the values as a list
                    values = [msg_id, date, alert] + [extracted_info[column.lower()] for column in self.STRATEGY_COLUMNS]
                    
                    
                    cursor.execute(
                        f'INSERT INTO alerts ({columns_line}) VALUES ({insertion_line})',
                        tuple(values)
                    )
                    conn.commit()
        
        if not alert_found:
            self.print_log('No new alerts found.')
    
        conn.close()
    
        return alert_found

    def check_database_update(self, last_checked_id):
        # Connect to the SQLite database
        conn = sqlite3.connect('tradingview_alerts.db')
        cursor = conn.cursor()
    
        # Query for new records since the last checked ID
        try:
            cursor.execute('SELECT * FROM alerts WHERE message_id > ?', (last_checked_id,))
            new_records = cursor.fetchall()
        except:
            return last_checked_id
    
        if new_records:
            # Process the new records
            for record in new_records:
                message_id, msg_timestamp, alert, *values = record
                #message = urllib.parse.unquote(message)
                
                # Print an alert message (you can customize the format) (REPLACE WITH TELEGRAM)
                line = f"New Alert: {alert}\n"
                for i, column_name in enumerate(self.STRATEGY_COLUMNS):
                    if i != len(self.STRATEGY_COLUMNS) -1:
                        line += f"{column_name.capitalize()}: {values[i]}\n"
                    else:
                        line += f"{column_name.capitalize()}: {values[i]}"
                
                if not self.initial_run:
                    print(line)
                    # self.notify_command(line)
                    self.message_queue.put(line)
                
                #print(line)
                ## self.notify_command(line)
                #self.message_queue.put(line)
            
            # Update the last_checked_id with the latest message_id
            last_checked_id = new_records[-1][0]
    
        # Close the database connection
        conn.close()
    
        return last_checked_id


    def store_alerts_daemon(self):
        while not self.start:
            time.sleep(1)
        
        OFFSET = 5 # seconds
        alert_found = False
        no_alerts_counter = 0
        while not self.kill_daemon:
            # to ensure no alerts found and recheck messages are not spamming
            if not alert_found and no_alerts_counter > 0:
                delete_last_line(2)
            
            try:
                alert_found = self.authenticate_and_fetch_alerts()
                
                if not alert_found:
                    self.initial_run = False
                    no_alerts_counter += 1
                else:
                    no_alerts_counter = 0
                
                # Calculate the number of seconds remaining in the current minute
                current_time = datetime.now()
                seconds_until_next_minute = 60 - current_time.second
                seconds_until_next_minute += OFFSET
                wait_time = seconds_until_next_minute % 11
                if wait_time < 2:
                    time.sleep(wait_time+1)
                    seconds_until_next_minute = 60 - current_time.second
                    seconds_until_next_minute += OFFSET
                    wait_time = seconds_until_next_minute % 11
                self.print_log(f"Checking again in {wait_time}s.")
                # Sleep for the remaining seconds until the next minute
                time.sleep(wait_time)
            except Exception as e:
                print(f"An error occurred: {e}")
                self.kill_daemon = True
                

    def process_new_alerts_daemon(self):
        while not self.start:
            time.sleep(1)
        TIMEOUT = 1
        # Initialize the last_checked_id (You can store it persistently)
        last_checked_id = 0
        loop_count = 0
        while not self.kill_daemon:
            try:
                last_checked_id = self.check_database_update(last_checked_id)
                time.sleep(TIMEOUT)  # Sleep for 1s
            except Exception as e:
                print(e)
                self.kill_daemon = True
    
    def print_log(self, text):
        current_time = datetime.now()
        timelog = current_time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timelog}] {text}")

    def run(self):
        os.system('clear')
        self.print_log("Launching TradingView Alerts data storing daemon...")
        background_thread(self.store_alerts_daemon, [])
        time.sleep(0.5)
        self.print_log("Launching TradingView Alerts alert processing daemon...")
        background_thread(self.process_new_alerts_daemon, [])
        time.sleep(0.5)
        self.print_log("Launching TradingView Alerts telegram messages daemon...")
        background_thread(self.message_daemon, [])
        time.sleep(0.5)
        self.print_log("TradingView Alerts handler is now live!")
        self.start = True

        # Loop until killed
        while not self.kill_daemon:
            time.sleep(5)
        
        # kill all threads

def background_thread(target, args_list):
    args = ()
    for arg in args_list:
        args += (arg,)
    pr = threading.Thread(target=target, args=args)
    pr.daemon = True
    pr.start()

# For deleting lines in stdout
def delete_last_line(num_lines=1):
    for i in range(num_lines):
        CURSOR_UP_ONE = '\033[F'
        ERASE_LINE = '\033[K'
        print(CURSOR_UP_ONE + ERASE_LINE, end='')


if __name__ == "__main__":
    while True:
        try:
            handler = TradingViewAlertsHandler()
            handler.run()
            # if background thread crashes
        except Exception as e:
            print(f"An error occurred: {e}")
            print("Restarting the script...")
            time.sleep(10)  # Wait for 10 seconds before restarting
