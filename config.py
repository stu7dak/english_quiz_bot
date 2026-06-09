import os

BOT_TOKEN = os.environ.get('BOT_TOKEN')
SHEET_NAME = os.environ.get('SHEET_NAME', 'Quiz_Statistics')
GOOGLE_CREDENTIALS_FILE = 'credentials.json'
MAX_ATTEMPTS = int(os.environ.get('MAX_ATTEMPTS', 3))
