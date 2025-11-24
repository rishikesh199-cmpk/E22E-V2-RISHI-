from pymongo import MongoClient
from datetime import datetime

MONGO_URL = "mongodb://localhost:27017"
client = MongoClient(MONGO_URL)

db = client["f324_database"]

users_col = db["users"]        # username, password
sessions_col = db["sessions"]  # automation sessions per user
logs_col = db["logs"]          # live logs per session
state_col = db["state"]        # running states
convos_col = db["conversations"]  # previous chat stores


def create_user(username, password):
    if users_col.find_one({"username": username}):
        return False
    users_col.insert_one({
        "username": username,
        "password": password,
        "created": datetime.utcnow()
    })
    return True


def save_session(user, chrome_profile_path, fb_id, status="stopped"):
    sessions_col.update_one(
        {"username": user},
        {
            "$set": {
                "chrome_profile": chrome_profile_path,
                "fb_id": fb_id,
                "status": status,
                "last_update": datetime.utcnow()
            }
        },
        upsert=True
    )


def update_status(user, status):
    state_col.update_one(
        {"username": user},
        {"$set": {"status": status}},
        upsert=True
    )


def get_status(user):
    doc = state_col.find_one({"username": user})
    if doc:
        return doc["status"]
    return "stopped"


def add_log(user, msg):
    logs_col.insert_one({
        "username": user,
        "msg": msg,
        "time": datetime.utcnow()
    })


def get_logs(user, limit=50):
    return list(
        logs_col.find({"username": user})
        .sort("time", -1)
        .limit(limit)
    )[:: -1]
