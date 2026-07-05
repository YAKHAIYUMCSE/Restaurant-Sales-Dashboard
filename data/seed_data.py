"""
Seed script — PRJ-053 Restaurant Sales Dashboard
PostgreSQL version
Run: python data/seed_data.py
"""
import random, os
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values

# ── DB connection ──────────────────────────────────────────────────────────────
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/restaurant_db")

MENU_ITEMS = [
    ("Chicken Biryani",      "Main Course",  220, 45),
    ("Mutton Biryani",       "Main Course",  280, 60),
    ("Veg Biryani",          "Main Course",  160, 30),
    ("Paneer Butter Masala", "Main Course",  180, 35),
    ("Dal Tadka",            "Main Course",  120, 20),
    ("Veg Fried Rice",       "Main Course",  140, 25),
    ("Fish Curry",           "Main Course",  240, 55),
    ("Egg Curry",            "Main Course",  150, 28),
    ("Curd Rice",            "Main Course",  100, 15),
    ("Butter Naan",          "Breads",        40,  8),
    ("Roti",                 "Breads",        20,  4),
    ("Parotta",              "Breads",        30,  6),
    ("Gulab Jamun",          "Desserts",      60, 12),
    ("Ice Cream",            "Desserts",      80, 15),
    ("Rasgulla",             "Desserts",      55, 10),
    ("Lassi",                "Beverages",     70, 12),
    ("Mango Juice",          "Beverages",     60, 10),
    ("Masala Tea",           "Beverages",     30,  5),
    ("Chicken 65",           "Starters",     180, 40),
    ("Onion Pakoda",         "Starters",      80, 15),
    ("Paneer Tikka",         "Starters",     160, 35),
    ("Veg Spring Roll",      "Starters",      90, 18),
]

PAYMENT_MODES = ["Cash", "UPI", "Card", "Online"]
ORDER_TYPES   = ["Dine-in", "Takeaway", "Delivery"]
STATUSES      = ["Completed", "Completed", "Completed", "Cancelled", "Refunded"]

NAMES = [
    "Arjun","Priya","Mohammed","Sneha","Karthik","Divya","Ravi","Anitha",
    "Suresh","Meena","Vikram","Lakshmi","Arun","Pooja","Ganesh","Revathi",
    "Deepak","Nithya","Bharath","Kavya","Harish","Sangeetha","Manoj","Selvi",
    "Praveen","Geetha","Venkat","Ammu","Sanjay","Nithyasri","Rahul","Fathima",
    "Dinesh","Saranya","Naveen","Brindha","Prashanth","Lavanya","Muthu","Vani",
    "Senthil","Janani","Balaji","Sumathi","Vijay","Malathi","Ramesh","Uma",
]
SURNAMES = ["Kumar","Raj","Devi","Selvan","Priya","Murthy","Rajan","Krishnan","Pillai","Nair"]


def seed():
    con = psycopg2.connect(DB_URL)
    cur = con.cursor()

    # ── Create tables ──────────────────────────────────────────────────────────
    cur.execute("""
        DROP TABLE IF EXISTS order_items CASCADE;
        DROP TABLE IF EXISTS orders      CASCADE;
        DROP TABLE IF EXISTS customers   CASCADE;
        DROP TABLE IF EXISTS menu_items  CASCADE;
        DROP TABLE IF EXISTS staff       CASCADE;

        CREATE TABLE menu_items (
            item_id   SERIAL PRIMARY KEY,
            name      TEXT    NOT NULL,
            category  TEXT    NOT NULL,
            price     NUMERIC(10,2) NOT NULL,
            cost      NUMERIC(10,2) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE
        );

        CREATE TABLE customers (
            customer_id SERIAL PRIMARY KEY,
            name        TEXT NOT NULL,
            phone       TEXT UNIQUE NOT NULL,
            email       TEXT,
            joined_on   DATE NOT NULL,
            loyalty_pts INTEGER DEFAULT 0
        );

        CREATE TABLE orders (
            order_id     SERIAL PRIMARY KEY,
            customer_id  INTEGER REFERENCES customers(customer_id),
            order_date   TIMESTAMP NOT NULL,
            order_type   TEXT NOT NULL,
            payment_mode TEXT NOT NULL,
            total_amount NUMERIC(10,2) NOT NULL,
            status       TEXT DEFAULT 'Completed',
            notes        TEXT
        );

        CREATE TABLE order_items (
            id         SERIAL PRIMARY KEY,
            order_id   INTEGER REFERENCES orders(order_id),
            item_id    INTEGER REFERENCES menu_items(item_id),
            quantity   INTEGER NOT NULL,
            unit_price NUMERIC(10,2) NOT NULL
        );

        CREATE TABLE staff (
            staff_id SERIAL PRIMARY KEY,
            name     TEXT NOT NULL,
            role     TEXT NOT NULL,
            shift    TEXT NOT NULL
        );

        CREATE INDEX idx_orders_date   ON orders(order_date);
        CREATE INDEX idx_orders_status ON orders(status);
        CREATE INDEX idx_oi_order      ON order_items(order_id);
        CREATE INDEX idx_oi_item       ON order_items(item_id);
    """)
    con.commit()

    # ── Menu items ─────────────────────────────────────────────────────────────
    execute_values(cur,
        "INSERT INTO menu_items (name, category, price, cost) VALUES %s",
        MENU_ITEMS
    )

    # ── Staff ──────────────────────────────────────────────────────────────────
    staff = [
        ("Rajan","Manager","Morning"), ("Selvam","Manager","Evening"),
        ("Muthu","Chef","Morning"),    ("Balu","Chef","Evening"),
        ("Priya","Waiter","Morning"),  ("Divya","Waiter","Evening"),
        ("Karthik","Waiter","Morning"),("Meena","Waiter","Evening"),
        ("Raj","Cashier","Morning"),   ("Uma","Cashier","Evening"),
    ]
    execute_values(cur,
        "INSERT INTO staff (name, role, shift) VALUES %s",
        staff
    )

    # ── Customers ──────────────────────────────────────────────────────────────
    phones_used = set()
    customers = []
    for i in range(200):
        name = random.choice(NAMES) + " " + random.choice(SURNAMES)
        while True:
            phone = f"9{random.randint(100000000,999999999)}"
            if phone not in phones_used:
                phones_used.add(phone); break
        email   = f"customer{i+1}@gmail.com"
        joined  = (datetime(2024,1,1) + timedelta(days=random.randint(0,400))).date()
        loyalty = random.randint(0, 500)
        customers.append((name, phone, email, joined, loyalty))
    execute_values(cur,
        "INSERT INTO customers (name, phone, email, joined_on, loyalty_pts) VALUES %s",
        customers
    )
    con.commit()

    # ── Fetch menu for order generation ───────────────────────────────────────
    cur.execute("SELECT item_id, price FROM menu_items")
    menu = cur.fetchall()  # [(item_id, price), ...]

    # ── Orders + order_items (90 days) ─────────────────────────────────────────
    start_date  = datetime(2025, 2, 1)
    order_rows  = []
    item_rows   = []   # parallel list of [(item_id, qty, price), ...]

    for day_offset in range(90):
        day = start_date + timedelta(days=day_offset)
        n   = random.randint(18,30) if day.weekday() >= 4 else random.randint(12,22)
        for _ in range(n):
            hour   = random.choices(
                [10,11,12,13,14,15,16,17,18,19,20,21],
                weights=[3,6,12,15,8,4,3,5,10,12,10,7]
            )[0]
            odate  = day + timedelta(hours=hour, minutes=random.randint(0,59))
            cid    = random.randint(1, 200)
            otype  = random.choice(ORDER_TYPES)
            pmode  = random.choice(PAYMENT_MODES)
            status = random.choices(STATUSES, weights=[70,70,70,5,3])[0]
            items  = random.sample(menu, random.randint(2,5))
            total, temp = 0, []
            for (iid, price) in items:
                qty    = random.randint(1, 3)
                total += qty * float(price)
                temp.append((iid, qty, float(price)))
            order_rows.append((cid, odate, otype, pmode, round(total,2), status))
            item_rows.append(temp)

    execute_values(cur,
        "INSERT INTO orders (customer_id, order_date, order_type, payment_mode, total_amount, status) VALUES %s RETURNING order_id",
        order_rows
    )
    oids = [r[0] for r in cur.fetchall()]

    flat = []
    for oid, items in zip(oids, item_rows):
        for (iid, qty, price) in items:
            flat.append((oid, iid, qty, price))
    execute_values(cur,
        "INSERT INTO order_items (order_id, item_id, quantity, unit_price) VALUES %s",
        flat
    )

    con.commit()
    con.close()
    print(f"✅ Seeded: {len(order_rows)} orders | 200 customers | {len(flat)} order-items | 22 menu items")


if __name__ == "__main__":
    seed()
