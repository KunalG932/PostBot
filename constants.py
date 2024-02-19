# router.py

from aiogram import Router
from aiogram import Dispatcher
from motor.motor_asyncio import AsyncIOMotorClient

mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["Postbot"]      

router = Router()

dp = Dispatcher()

TOKEN = "6753603405:AAEXkgfWXPiBr_TGynYIpyCEwEeDg-Ax_Ec"
CHANNEL_ID = -1001824676870
MONGO_URI = "mongodb+srv://exp69:exp69@cluster0.kr93qbe.mongodb.net/?retryWrites=true&w=majority"
