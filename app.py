from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "smart_campus.db"

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

CATEGORIES = ["Identity Card", "Books", "Electronics", "Bags", "Other"]
STATUSES = ["Open", "Claim Pending", "Returned", "Closed"]

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'student',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        item_type TEXT NOT NULL CHECK(item_type IN ('lost','found')),
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        location TEXT NOT NULL,
        item_date TEXT NOT NULL,
        item_time TEXT,
        status TEXT NOT NULL DEFAULT 'Open',
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        claimant_id INTEGER NOT NULL,
        proof TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        created_at TEXT NOT NULL,
        FOREIGN KEY(item_id) REFERENCES items(id),
        FOREIGN KEY(claimant_id) REFERENCES users(id)
    );
    """)
    conn.commit()

    # Demo account for testing
    demo = conn.execute("SELECT id FROM users WHERE email=?", ("student@college.edu",)).fetchone()
    if not demo:
        conn.execute(
            "INSERT INTO users (name,email,password,role,created_at) VALUES (?,?,?,?,?)",
            ("Demo Student", "student@college.edu",
             generate_password_hash("123456"), "student",
             datetime.now().isoformat(timespec="seconds"))
        )
        conn.commit()
    conn.close()

def logged_in():
    return "user_id" in session

@app.route("/")
def index():
    if logged_in():
        return redirect(url_for("home"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]
            return redirect(url_for("home"))

        flash("Invalid email or password.", "error")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 6:
            flash("Enter all details. Password must be at least 6 characters.", "error")
            return render_template("register.html")

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (name,email,password,role,created_at) VALUES (?,?,?,?,?)",
                (name, email, generate_password_hash(password), "student",
                 datetime.now().isoformat(timespec="seconds"))
            )
            conn.commit()
            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "error")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/home")
def home():
    if not logged_in():
        return redirect(url_for("login"))

    conn = get_db()
    stats = {
        "lost": conn.execute("SELECT COUNT(*) FROM items WHERE item_type='lost'").fetchone()[0],
        "found": conn.execute("SELECT COUNT(*) FROM items WHERE item_type='found'").fetchone()[0],
        "returned": conn.execute("SELECT COUNT(*) FROM items WHERE status='Returned'").fetchone()[0],
        "claims": conn.execute("SELECT COUNT(*) FROM claims WHERE status='Pending'").fetchone()[0],
    }
    recent = conn.execute("""
        SELECT items.*, users.name AS reporter
        FROM items JOIN users ON users.id=items.user_id
        ORDER BY items.id DESC LIMIT 6
    """).fetchall()
    conn.close()
    return render_template("home.html", stats=stats, recent=recent)

@app.route("/report/<item_type>", methods=["GET", "POST"])
def report(item_type):
    if not logged_in():
        return redirect(url_for("login"))
    if item_type not in ("lost", "found"):
        return "Invalid item type", 404

    if request.method == "POST":
        data = (
            session["user_id"],
            item_type,
            request.form.get("name", "").strip(),
            request.form.get("category", "").strip(),
            request.form.get("description", "").strip(),
            request.form.get("location", "").strip(),
            request.form.get("item_date", "").strip(),
            request.form.get("item_time", "").strip(),
            datetime.now().isoformat(timespec="seconds")
        )
        if not all(data[2:8]):
            flash("Please fill in all required fields.", "error")
            return render_template("report.html", item_type=item_type, categories=CATEGORIES)
        conn = get_db()
        conn.execute("""
            INSERT INTO items
            (user_id,item_type,name,category,description,location,item_date,item_time,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, data)
        conn.commit()
        conn.close()
        flash(f"{item_type.title()} item reported successfully.", "success")
        return redirect(url_for("home"))

    return render_template("report.html", item_type=item_type, categories=CATEGORIES)

@app.route("/search")
def search():
    if not logged_in():
        return redirect(url_for("login"))

    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    sql = """
        SELECT items.*, users.name AS reporter
        FROM items JOIN users ON users.id=items.user_id
        WHERE 1=1
    """
    params = []
    if q:
        sql += """ AND (items.name LIKE ? OR items.description LIKE ?
                       OR items.location LIKE ? OR items.category LIKE ?)"""
        term = f"%{q}%"
        params += [term, term, term, term]
    if category:
        sql += " AND items.category=?"
        params.append(category)

    sql += " ORDER BY items.id DESC"
    conn = get_db()
    items = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template("search.html", items=items, q=q, category=category, categories=CATEGORIES)

@app.route("/matches/<int:item_id>")
def matches(item_id):
    if not logged_in():
        return redirect(url_for("login"))
    conn = get_db()
    item = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if not item:
        conn.close()
        return "Item not found", 404

    opposite = "found" if item["item_type"] == "lost" else "lost"
    candidates = conn.execute("""
        SELECT * FROM items
        WHERE item_type=? AND id<>? AND status='Open'
    """, (opposite, item_id)).fetchall()
    conn.close()

    # Simple text/attribute similarity for the mini-project prototype.
    source_words = set((item["name"] + " " + item["description"]).lower().split())
    ranked = []
    for candidate in candidates:
        target_words = set((candidate["name"] + " " + candidate["description"]).lower().split())
        score = len(source_words & target_words) * 20
        if candidate["category"].lower() == item["category"].lower():
            score += 30
        if candidate["location"].lower() == item["location"].lower():
            score += 25
        ranked.append((min(score, 100), candidate))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return render_template("matches.html", item=item, matches=ranked[:10])

@app.route("/claim/<int:item_id>", methods=["GET", "POST"])
def claim(item_id):
    if not logged_in():
        return redirect(url_for("login"))
    conn = get_db()
    item = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    conn.close()
    if not item or item["item_type"] != "found":
        return "Found item not available for claim", 404

    if request.method == "POST":
        proof = request.form.get("proof", "").strip()
        if not proof:
            flash("Please provide identifying information for verification.", "error")
            return render_template("claim.html", item=item)

        conn = get_db()
        conn.execute(
            "INSERT INTO claims (item_id,claimant_id,proof,created_at) VALUES (?,?,?,?)",
            (item_id, session["user_id"], proof, datetime.now().isoformat(timespec="seconds"))
        )
        conn.execute("UPDATE items SET status='Claim Pending' WHERE id=?", (item_id,))
        conn.commit()
        conn.close()
        flash("Claim submitted for verification.", "success")
        return redirect(url_for("home"))

    return render_template("claim.html", item=item)

@app.route("/my-claims")
def my_claims():
    if not logged_in():
        return redirect(url_for("login"))
    conn = get_db()
    claims = conn.execute("""
        SELECT claims.*, items.name AS item_name, items.location, items.status AS item_status
        FROM claims JOIN items ON items.id=claims.item_id
        WHERE claims.claimant_id=?
        ORDER BY claims.id DESC
    """, (session["user_id"],)).fetchall()
    conn.close()
    return render_template("claims.html", claims=claims)

@app.route("/admin")
def admin():
    if not logged_in() or session.get("role") != "admin":
        return "Admin access required", 403
    conn = get_db()
    users = conn.execute("SELECT id,name,email,role,created_at FROM users ORDER BY id DESC").fetchall()
    items = conn.execute("""
        SELECT items.*, users.name AS reporter
        FROM items JOIN users ON users.id=items.user_id ORDER BY items.id DESC
    """).fetchall()
    claims = conn.execute("""
        SELECT claims.*, items.name AS item_name, users.name AS claimant
        FROM claims JOIN items ON items.id=claims.item_id
        JOIN users ON users.id=claims.claimant_id
        ORDER BY claims.id DESC
    """).fetchall()
    conn.close()
    return render_template("admin.html", users=users, items=items, claims=claims)

@app.route("/api/stats")
def api_stats():
    conn = get_db()
    result = {
        "lost": conn.execute("SELECT COUNT(*) FROM items WHERE item_type='lost'").fetchone()[0],
        "found": conn.execute("SELECT COUNT(*) FROM items WHERE item_type='found'").fetchone()[0],
        "returned": conn.execute("SELECT COUNT(*) FROM items WHERE status='Returned'").fetchone()[0],
        "pending_claims": conn.execute("SELECT COUNT(*) FROM claims WHERE status='Pending'").fetchone()[0],
    }
    conn.close()
    return jsonify(result)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
