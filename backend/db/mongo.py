import os
from typing import Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


def get_mongo_config() -> Tuple[Optional[str], str]:
    uri = os.getenv("MONGODB_URI") or os.getenv("SOAC_MONGODB_URI")
    db_name = os.getenv("MONGODB_DB") or os.getenv("SOAC_MONGODB_DB") or "soac"
    return uri, db_name


async def create_mongo_client() -> Tuple[Optional[AsyncIOMotorClient], Optional[AsyncIOMotorDatabase]]:
    uri, db_name = get_mongo_config()
    if not uri:
        return None, None
    client = AsyncIOMotorClient(uri)
    db = client[db_name]
    await db.command("ping")
    return client, db


async def close_mongo_client(client: Optional[AsyncIOMotorClient]) -> None:
    if client is None:
        return
    client.close()
