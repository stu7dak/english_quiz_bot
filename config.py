import os

BOT_TOKEN = os.environ.get('8906119391:AAEoXLHvRniRiVC49uxPGqWnDMSxI5lgPmc')
SHEET_NAME = os.environ.get('SHEET_NAME', 'Лист1')
GOOGLE_CREDENTIALS_FILE = 'credentials.json'
MAX_ATTEMPTS = int(os.environ.get('MAX_ATTEMPTS', 3))
