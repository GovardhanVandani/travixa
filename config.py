import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-2024-travixa'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///travixa.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID') or ''
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN') or ''
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER') or ''
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY') or ''