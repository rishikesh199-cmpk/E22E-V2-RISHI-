from pymongo import MongoClient
from datetime import datetime

client = MongoClient("mongodb://localhost:27017/")
db = client["automation_db"]

users_col = db["users"]
convos_col = db["conversations"]


def create_user(username, password):
    if users_col.find_one({"username": username}):
        print("User exists")
        return

    users_col.insert_one({
        "username": username,
        "password": password,
        "created_at": datetime.utcnow()
    })

    print("User created:", username)


if __name__ == "__main__":
    u = input("Username: ")
    p = input("Password: ")
    create_user(u, p)
