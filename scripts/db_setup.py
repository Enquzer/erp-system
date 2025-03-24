import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_code TEXT NOT NULL,
        product_name TEXT NOT NULL,
        product_image TEXT,
        product_description TEXT,
        category TEXT,
        campaign_type TEXT,
        produced_quantity INTEGER,
        released_quantity INTEGER
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS inventory_breakdown (
        breakdown_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        color TEXT,
        size TEXT,
        quantity INTEGER,
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT NOT NULL,
        product_id INTEGER,
        color TEXT,
        size TEXT,
        quantity INTEGER,
        order_date TEXT,
        expected_delivery_date TEXT,
        is_urgent INTEGER,
        comments TEXT,
        status TEXT,
        received_date TEXT,
        adjustment_comments TEXT,
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )''')

    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", ("factory_admin", "factory123", "factory"))
    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", ("shop_admin", "shop123", "shop"))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")