import os

BOT_TOKEN = os.environ.get('8906119391:AAGtkFXAHd1y_En8Wdr_UM_z-WN9X41R300')
SHEET_NAME = os.environ.get('SHEET_NAME', 'Quiz_Statistics')
GOOGLE_CREDENTIALS_FILE = 'credentials.json'
MAX_ATTEMPTS = int(os.environ.get('MAX_ATTEMPTS', 3))
