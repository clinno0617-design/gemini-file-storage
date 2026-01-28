from db_manager import DatabaseManager

db = DatabaseManager()
if db.connect():
    print("✅ 資料庫連線成功!")
    stats = db.get_statistics()
    print(f"統計資料: {stats}")
    db.close()
else:
    print("❌ 資料庫連線失敗")