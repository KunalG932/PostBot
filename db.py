from motor.motor_asyncio import AsyncIOMotorClient

from constants import MONGO_URI

mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["Postbot"]
