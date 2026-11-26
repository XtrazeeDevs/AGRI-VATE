"""
Todoroki Market - Python recreation
Run:
    py -m pip install flask
    py app.py
Then open http://127.0.0.1:5000

This is a clean-room recreation of the visible marketplace features found
in the supplied executable. It is not recovered original source code.
"""
from flask import Flask, request, redirect, url_for, session, flash, render_template_string, abort
import sqlite3
import os
import uuid
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "todoroki_market.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("TODOROKI_SECRET", "change-this-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
CATEGORIES = ["Electronics", "Fashion", "Food", "Home", "Other"]

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL,
            description TEXT DEFAULT '',
            photo TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(seller_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buyer_id INTEGER NOT NULL,
            total REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Processing',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(buyer_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
        """)
init_db()

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    with db() as con:
        return con.execute("SELECT id,name,email FROM users WHERE id=?", (uid,)).fetchone()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_cart():
    return session.get("cart", {})

def cart_details():
    cart = get_cart()
    if not cart:
        return [], 0
    ids = [int(i) for i in cart.keys()]
    marks = ",".join("?" for _ in ids)
    with db() as con:
        rows = con.execute(f"SELECT * FROM products WHERE id IN ({marks})", ids).fetchall()
    items, total = [], 0
    for p in rows:
        qty = int(cart.get(str(p["id"]), 0))
        if qty > 0:
            line = p["price"] * qty
            items.append({"product": p, "qty": qty, "line": line})
            total += line
    return items, total

BASE = r"""
<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }} - Todoroki Market</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:#f5f7fb;color:#18212f}
nav{background:#111827;color:white;padding:14px 5%;display:flex;align-items:center;gap:18px;flex-wrap:wrap}
nav a{color:white;text-decoration:none}.brand{font-weight:800;font-size:20px;margin-right:auto}
.wrap{max-width:1100px;margin:30px auto;padding:0 18px}.hero{background:linear-gradient(135deg,#14532d,#16a34a);color:white;border-radius:20px;padding:34px;margin-bottom:24px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px}
.card{background:white;border-radius:16px;padding:18px;box-shadow:0 8px 28px #00000010}
.product img{width:100%;height:180px;object-fit:cover;border-radius:12px;background:#e5e7eb}
.price{font-size:20px;font-weight:800;color:#15803d}.muted{color:#64748b}
.btn{display:inline-block;border:0;border-radius:10px;background:#16a34a;color:white;padding:10px 15px;text-decoration:none;cursor:pointer;font-size:14px}
.btn.dark{background:#111827}.btn.red{background:#dc2626}.btn.light{background:#e2e8f0;color:#111827}
.input{width:100%;padding:11px;border:1px solid #cbd5e1;border-radius:9px;margin:6px 0 14px;font:inherit}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.notice{padding:12px;border-radius:10px;background:#dcfce7;color:#166534;margin-bottom:16px}
.notice.error{background:#fee2e2;color:#991b1b}.table{width:100%;border-collapse:collapse;background:white}
.table td,.table th{padding:12px;border-bottom:1px solid #e2e8f0;text-align:left}.small{font-size:13px}
footer{padding:30px;text-align:center;color:#64748b}textarea{resize:vertical}
@media(max-width:600px){nav{gap:12px}.brand{width:100%}.table{font-size:13px}}
</style></head><body>
<nav><a class="brand" href="{{ url_for('shop') }}">TODOROKI MARKET</a>
<a href="{{ url_for('shop') }}">Shop</a><a href="{{ url_for('sell') }}">Sell</a>
<a href="{{ url_for('cart') }}">Cart ({{ cart_count }})</a>
{% if user %}<span>Hi, {{ user.name }}</span><a href="{{ url_for('orders') }}">Orders</a><a href="{{ url_for('logout') }}">Logout</a>
{% else %}<a href="{{ url_for('login') }}">Login</a><a href="{{ url_for('register') }}">Register</a>{% endif %}
</nav><main class="wrap">
{% with messages = get_flashed_messages(with_categories=true) %}{% for category,message in messages %}
<div class="notice {{ 'error' if category=='error' else '' }}">{{ message }}</div>{% endfor %}{% endwith %}
{{ body|safe }}</main><footer>Todoroki Market · Buy and sell anything.</footer></body></html>
"""

def page(title, body, **context):
    cart_count = sum(int(v) for v in get_cart().values())
    return render_template_string(BASE, title=title, body=render_template_string(body, **context),
                                  user=current_user(), cart_count=cart_count)

@app.route("/")
def shop():
    q = request.args.get("q", "").strip()
    cat = request.args.get("cat", "").strip()
    sql = "SELECT p.*,u.name AS seller FROM products p JOIN users u ON u.id=p.seller_id WHERE p.stock>0"
    args = []
    if q:
        sql += " AND (p.name LIKE ? OR p.description LIKE ?)"
        args += [f"%{q}%", f"%{q}%"]
    if cat in CATEGORIES:
        sql += " AND p.category=?"
        args.append(cat)
    sql += " ORDER BY p.created_at DESC"
    with db() as con:
        products = con.execute(sql, args).fetchall()
    body = r"""
    <section class="hero"><h1>Buy &amp; sell anything.</h1>
    <p>Open a shop, upload product photos, manage stock and sell directly.</p>
    <form class="row" method="get"><input class="input" style="max-width:500px;margin:0" name="q" placeholder="Search products..." value="{{ q }}">
    <button class="btn dark">Search</button></form></section>
    <div class="row" style="margin-bottom:18px"><a class="btn light" href="/">All</a>
    {% for c in categories %}<a class="btn light" href="/?cat={{ c }}">{{ c }}</a>{% endfor %}</div>
    {% if products %}<div class="grid">{% for p in products %}<div class="card product">
    {% if p.photo %}<img src="{{ url_for('uploaded_file', filename=p.photo) }}" alt="{{ p.name }}">{% else %}<div style="height:180px;background:#e5e7eb;border-radius:12px;display:grid;place-items:center;color:#64748b">No photo</div>{% endif %}
    <h3>{{ p.name }}</h3><div class="muted">{{ p.category }} · Seller: {{ p.seller }}</div>
    <p>{{ p.description }}</p><div class="price">₱{{ "%.2f"|format(p.price) }}</div>
    <p class="small">{{ p.stock }} in stock</p><form method="post" action="{{ url_for('add_cart', product_id=p.id) }}">
    <button class="btn">Add to cart</button></form></div>{% endfor %}</div>
    {% else %}<div class="card"><h3>No products found</h3><p class="muted">Try another search or category.</p></div>{% endif %}
    """
    return page("Shop", body, products=products, q=q, categories=CATEGORIES)

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    from flask import send_from_directory
    return send_from_directory(UPLOAD_DIR, filename)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 6:
            flash("Enter your name and email, and use a password with at least 6 characters.", "error")
        else:
            try:
                with db() as con:
                    con.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)",
                                (name, email, generate_password_hash(password)))
                flash("Account created. You can now log in.")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That email is already registered.", "error")
    body = r"""<div class="card" style="max-width:480px;margin:auto"><h2>Create account</h2>
    <form method="post"><label>Full name</label><input class="input" name="name" required>
    <label>Email</label><input class="input" type="email" name="email" required>
    <label>Password</label><input class="input" type="password" name="password" minlength="6" required>
    <button class="btn">Register</button></form></div>"""
    return page("Register", body)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with db() as con:
            user = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["cart"] = {}
            return redirect(url_for("shop"))
        flash("Invalid email or password.", "error")
    body = r"""<div class="card" style="max-width:480px;margin:auto"><h2>Login</h2>
    <form method="post"><label>Email</label><input class="input" type="email" name="email" required>
    <label>Password</label><input class="input" type="password" name="password" required>
    <button class="btn">Login</button></form><p class="small">No account? <a href="{{ url_for('register') }}">Register here</a>.</p></div>"""
    return page("Login", body)

@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out.")
    return redirect(url_for("shop"))

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "Other")
        description = request.form.get("description", "").strip()
        try:
            price = float(request.form.get("price", "0"))
            stock = int(request.form.get("stock", "-1"))
        except ValueError:
            price, stock = 0, -1
        photo = request.files.get("photo")
        if not name or category not in CATEGORIES or price <= 0 or stock < 0:
            flash("Please enter a valid name, category, price, and stock.", "error")
        elif photo and photo.filename and not allowed_file(photo.filename):
            flash("Photo must be JPG, JPEG, PNG, or WEBP.", "error")
        else:
            filename = ""
            if photo and photo.filename:
                ext = secure_filename(photo.filename).rsplit(".", 1)[1].lower()
                filename = uuid.uuid4().hex + "." + ext
                photo.save(os.path.join(UPLOAD_DIR, filename))
            with db() as con:
                con.execute("""INSERT INTO products(seller_id,name,category,price,stock,description,photo)
                               VALUES(?,?,?,?,?,?,?)""",
                            (session["user_id"], name, category, price, stock, description, filename))
            flash("Your product has been published.")
            return redirect(url_for("sell"))
    with db() as con:
        listings = con.execute("SELECT * FROM products WHERE seller_id=? ORDER BY id DESC",
                               (session["user_id"],)).fetchall()
    body = r"""<div class="card"><h2>Sell a product</h2>
    <form method="post" enctype="multipart/form-data"><div class="grid">
    <div><label>Product name</label><input class="input" name="name" required>
    <label>Category</label><select class="input" name="category">{% for c in categories %}<option>{{ c }}</option>{% endfor %}</select>
    <label>Price (₱)</label><input class="input" name="price" type="number" step="0.01" min="0.01" required></div>
    <div><label>Stock</label><input class="input" name="stock" type="number" min="0" required>
    <label>Product photo</label><input class="input" name="photo" type="file" accept="image/jpeg,image/png,image/webp">
    <label>Description</label><textarea class="input" name="description" rows="4"></textarea></div></div>
    <button class="btn">Publish item</button></form></div>
    <div class="card" style="margin-top:20px"><h2>Your listings</h2>
    {% if listings %}<table class="table"><tr><th>Product</th><th>Price</th><th>Stock</th><th></th></tr>
    {% for p in listings %}<tr><td>{{ p.name }}</td><td>₱{{ "%.2f"|format(p.price) }}</td><td>{{ p.stock }}</td>
    <td><form method="post" action="{{ url_for('delete_product', product_id=p.id) }}" onsubmit="return confirm('Delete this listing?')">
    <button class="btn red">Delete</button></form></td></tr>{% endfor %}</table>{% else %}<p class="muted">You have no listings yet.</p>{% endif %}</div>"""
    return page("Sell", body, listings=listings, categories=CATEGORIES)

@app.route("/product/<int:product_id>/delete", methods=["POST"])
@login_required
def delete_product(product_id):
    with db() as con:
        con.execute("DELETE FROM products WHERE id=? AND seller_id=?", (product_id, session["user_id"]))
    cart = get_cart()
    cart.pop(str(product_id), None)
    session["cart"] = cart
    flash("Listing deleted.")
    return redirect(url_for("sell"))

@app.route("/cart/add/<int:product_id>", methods=["POST"])
def add_cart(product_id):
    with db() as con:
        product = con.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not product or product["stock"] <= 0:
        flash("This product is unavailable.", "error")
        return redirect(url_for("shop"))
    cart = get_cart()
    key = str(product_id)
    cart[key] = min(int(cart.get(key, 0)) + 1, product["stock"])
    session["cart"] = cart
    flash("Product added to cart.")
    return redirect(request.referrer or url_for("shop"))

@app.route("/cart")
def cart():
    items, total = cart_details()
    body = r"""<h1>Your cart</h1><div class="card">
    {% if items %}<table class="table"><tr><th>Item</th><th>Price</th><th>Qty</th><th>Total</th><th></th></tr>
    {% for item in items %}<tr><td>{{ item.product.name }}</td><td>₱{{ "%.2f"|format(item.product.price) }}</td>
    <td><form class="row" method="post" action="{{ url_for('update_cart', product_id=item.product.id) }}">
    <input class="input" style="width:75px;margin:0" type="number" min="0" max="{{ item.product.stock }}" name="qty" value="{{ item.qty }}">
    <button class="btn light">Update</button></form></td><td>₱{{ "%.2f"|format(item.line) }}</td>
    <td><form method="post" action="{{ url_for('remove_cart', product_id=item.product.id) }}"><button class="btn red">Remove</button></form></td></tr>{% endfor %}</table>
    <h2 style="text-align:right">Total: ₱{{ "%.2f"|format(total) }}</h2>
    <form method="post" action="{{ url_for('checkout') }}"><button class="btn">Checkout</button></form>
    {% else %}<p>Your cart is empty.</p><a class="btn" href="{{ url_for('shop') }}">Browse products</a>{% endif %}</div>"""
    return page("Cart", body, items=items, total=total)

@app.route("/cart/update/<int:product_id>", methods=["POST"])
def update_cart(product_id):
    try:
        qty = int(request.form.get("qty", "0"))
    except ValueError:
        qty = 0
    with db() as con:
        p = con.execute("SELECT stock FROM products WHERE id=?", (product_id,)).fetchone()
    cart = get_cart()
    if p and qty > 0:
        cart[str(product_id)] = min(qty, p["stock"])
    else:
        cart.pop(str(product_id), None)
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/cart/remove/<int:product_id>", methods=["POST"])
def remove_cart(product_id):
    cart = get_cart()
    cart.pop(str(product_id), None)
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/checkout", methods=["POST"])
@login_required
def checkout():
    items, total = cart_details()
    if not items:
        flash("Your cart is empty.", "error")
        return redirect(url_for("cart"))
    try:
        with db() as con:
            # Re-check stock and create the order atomically.
            for item in items:
                current = con.execute("SELECT stock FROM products WHERE id=?", (item["product"]["id"],)).fetchone()
                if not current or current["stock"] < item["qty"]:
                    raise ValueError(f"Not enough stock for {item['product']['name']}.")
            cur = con.execute("INSERT INTO orders(buyer_id,total) VALUES(?,?)",
                              (session["user_id"], total))
            order_id = cur.lastrowid
            for item in items:
                p = item["product"]
                con.execute("INSERT INTO order_items(order_id,product_id,product_name,price,quantity) VALUES(?,?,?,?,?)",
                            (order_id, p["id"], p["name"], p["price"], item["qty"]))
                con.execute("UPDATE products SET stock=stock-? WHERE id=?", (item["qty"], p["id"]))
        session["cart"] = {}
        flash(f"Order #{order_id} placed successfully.")
        return redirect(url_for("orders"))
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("cart"))

@app.route("/orders")
@login_required
def orders():
    with db() as con:
        rows = con.execute("SELECT * FROM orders WHERE buyer_id=? ORDER BY id DESC",
                           (session["user_id"],)).fetchall()
        details = {}
        for order in rows:
            details[order["id"]] = con.execute("SELECT * FROM order_items WHERE order_id=?",
                                                (order["id"],)).fetchall()
    body = r"""<h1>Your orders</h1>{% if orders %}<div class="card"><table class="table">
    <tr><th>Order</th><th>Items</th><th>Total</th><th>Status</th><th>Date</th></tr>
    {% for o in orders %}<tr><td>#{{ o.id }}</td><td>{% for i in details[o.id] %}{{ i.product_name }} × {{ i.quantity }}<br>{% endfor %}</td>
    <td>₱{{ "%.2f"|format(o.total) }}</td><td>{{ o.status }}</td><td>{{ o.created_at }}</td></tr>{% endfor %}</table></div>
    {% else %}<div class="card"><p>You have no orders yet.</p><a class="btn" href="{{ url_for('shop') }}">Start shopping</a></div>{% endif %}"""
    return page("Orders", body, orders=rows, details=details)

@app.errorhandler(413)
def too_large(_):
    flash("The uploaded photo is too large. Maximum size is 5 MB.", "error")
    return redirect(request.referrer or url_for("sell"))

if __name__ == "__main__":
    print("Todoroki Market is running at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
