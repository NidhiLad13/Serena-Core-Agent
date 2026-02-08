# services/mongo.py
from pymongo import MongoClient
from app.config.settings import settings

client = MongoClient(settings.MONGODB_URI)
db = client.serena
