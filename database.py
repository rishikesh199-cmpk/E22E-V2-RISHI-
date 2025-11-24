from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["automation_db"]

users_col = db["users"]
logs_col = db["logs"]
state_col = db["state"]
convos_col = db["conversations"]
