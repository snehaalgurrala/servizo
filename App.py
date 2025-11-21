# app.py
from helpers import get_db_connection, hash_password, check_password
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import base64, bcrypt
from werkzeug.security import generate_password_hash
hashed_pw = generate_password_hash("Snehaal@123")  # replace admin123 with your password
# Then insert into DB
#INSERT INTO admins (name,email,password) VALUES ('Admin','admin@example.com','<hashed_pw>');

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "change-this-secret-to-a-secure-one")

@app.route("/")
def home():
    return render_template("home.html")

# ---------------------------
# ROOT / INDEX - single handler
# ---------------------------
@app.route("/")
def index():
    # If any of the user types are logged in, redirect appropriately
    if session.get("admin"):
        return redirect(url_for("admin_dashboard"))
    if session.get("captain"):
        return redirect(url_for("captain_dashboard"))
    if session.get("customer"):
        return redirect(url_for("customer_dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name").strip()
        email = request.form.get("email").strip()
        phone = request.form.get("phone").strip()
        password = request.form.get("password")
        address = request.form.get("address").strip()
        gated = request.form.get("gated")
        if gated == "yes":
            community_type = "gated"
            community_name = request.form.get("community_name").strip()
            block_or_house = request.form.get("block_or_house").strip()
        else:
            community_type = "non-gated"
            community_name_input = request.form.get("community_name_non", "").strip()
            community_name = community_name_input if community_name_input else None
            block_or_house = request.form.get("block_or_house_non").strip()

        # Basic validation
        if not (name and email and phone and password):
            flash("Please fill required fields", "danger")
            return redirect(url_for("register"))

        # Hash password
        hashed = hash_password(password)

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO customers
                (name, email, phone, password, address, community_type, community_name, block_or_house)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, email, phone, hashed, address, community_type, community_name, block_or_house))
            conn.commit()
            cur.close()
            conn.close()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Error during registration: {e}", "danger")
            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("identifier").strip()
        password = request.form.get("password")

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        # determine email or phone
        if "@" in identifier and "." in identifier:
            cur.execute("SELECT * FROM customers WHERE email=%s", (identifier,))
        else:
            cur.execute("SELECT * FROM customers WHERE phone=%s", (identifier,))

        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row or not check_password(password, row['password']):
            flash("Invalid credentials", "danger")
            return redirect(url_for("login"))

        # success - create session
        session['customer_id'] = row['id']
        session['customer_name'] = row['name']
        flash(f"Welcome {row['name']}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if not session.get("customer_id"):
        return redirect(url_for("customer_dashboard"))

    customer_id = session['customer_id']
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # small example: fetch orders for this customer
    cur.execute("""
        SELECT o.id AS order_id, s.name AS service_name, o.order_date, o.status
        FROM orders o
        LEFT JOIN services s ON o.service_id = s.id
        WHERE o.customer_id = %s
        ORDER BY o.order_date DESC
    """, (customer_id,))
    orders = cur.fetchall()

    cur.execute("SELECT id, name, price, description FROM services")
    services = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("dashboard.html", name=session.get("customer_name"), orders=orders, services=services)


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("index"))

@app.route("/customer/register", methods=["GET", "POST"])
def customer_register():
    if request.method == "POST":
        name = request.form["name"].strip()
        phone = request.form["phone"].strip()
        email = request.form["email"].strip()
        password = request.form["password"].strip()
        confirm_password = request.form["confirm_password"].strip()
        address = request.form["address"].strip()
        community_type = request.form.get("community_type")
        community_name = request.form.get("community_name") or None
        block_or_house = request.form["block_or_house"].strip()

        if not phone.isdigit():
            flash("❌ Invalid phone number. Digits only.", "danger")
            return redirect(url_for("customer_register"))

        if password != confirm_password:
            flash("❌ Passwords do not match.", "danger")
            return redirect(url_for("customer_register"))

        hashed_str = hash_password(password)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO customers
                (name, email, phone, password, address, community_type, community_name, block_or_house)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, email, phone, hashed_str, address, community_type, community_name, block_or_house))

            conn.commit()
            cursor.close()
            conn.close()

            flash("✅ Registration successful! Please login.", "success")
            return redirect(url_for("customer_login"))

        except mysql.connector.Error as err:
            flash(f"❌ Error while registering: {err}", "danger")
            return redirect(url_for("customer_register"))

    return render_template("customer_register.html")

@app.route("/customer/login", methods=["GET", "POST"])
def customer_login():
    if request.method == "POST":
        identifier = request.form["identifier"].strip()
        password = request.form["password"].strip()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if "@" in identifier and "." in identifier:
            cursor.execute("SELECT * FROM customers WHERE email=%s", (identifier,))
        else:
            cursor.execute("SELECT * FROM customers WHERE phone=%s", (identifier,))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row:
            stored_hash_bytes = base64.b64decode(row['password'])
            if bcrypt.checkpw(password.encode("utf-8"), stored_hash_bytes):
                session["customer"] = {"id": row["id"], "name": row["name"]}
                flash(f"✅ Welcome back, {row['name']}!", "success")
                return redirect(url_for("customer_dashboard"))
            else:
                flash("❌ Incorrect password.", "danger")
        else:
            flash("❌ Account not found.", "danger")

    #session['customer_id'] = customer.id
    return render_template("customer_login.html")


@app.route("/customer/dashboard")
def customer_dashboard():
    if "customer" not in session:
        flash("⚠️ Please log in first.", "danger")
        return redirect(url_for("customer_login"))

    customer = session["customer"]
    return render_template("customer_dashboard.html", customer=customer)


@app.route("/customer/logout")
def logout_customer():
    session.pop("customer", None)
    flash("✅ You have been logged out.", "success")
    return redirect(url_for("home"))

@app.route("/customer/services")
def customer_services():
    if "customer" not in session:
        flash("⚠️ Please log in first.", "danger")
        return redirect(url_for("customer_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM services")
    services = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("customer_services.html", services=services)


@app.route('/customer/book/<int:service_id>', methods=['POST'])
def book_service(service_id):
    if "customer" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("customer_login"))

    customer_id = session["customer"]["id"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO orders (customer_id, service_id, status) VALUES (%s, %s, %s)",
        (customer_id, service_id, "Pending")
    )
    conn.commit()
    cur.close()
    conn.close()

    flash("Service booked successfully!", "success")
    return redirect(url_for("view_orders"))

@app.route("/customer/orders")
def view_orders():
    if "customer" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("customer_login"))

    customer_id = session["customer"]["id"]

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT o.id AS order_id, s.name AS service_name, s.price,
               o.status, o.order_date, c.id AS captain_id, c.name AS captain_name,
               IF(r.id IS NULL, 0, 1) AS already_rated
        FROM orders o
        JOIN services s ON o.service_id = s.id
        LEFT JOIN captains c ON o.captain_id = c.id
        LEFT JOIN ratings r ON r.order_id = o.id AND r.customer_id = %s
        WHERE o.customer_id = %s
        ORDER BY o.order_date DESC
    """, (customer_id, customer_id))

    orders = cur.fetchall()
    cur.close()
    conn.close()

    print("Orders fetched:", orders)  # Debug: see what you get
    return render_template("customer_orders.html", orders=orders)



@app.route('/customer/cancel/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    # Correct session check
    if "customer" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("customer_login"))

    customer_id = session["customer"]["id"]

    conn = get_db_connection()
    cur = conn.cursor()

    # Check order exists and belongs to customer AND is pending
    cur.execute("SELECT status FROM orders WHERE id=%s AND customer_id=%s",
                (order_id, customer_id))
    order = cur.fetchone()

    if order and order[0] == "Pending":
        cur.execute("UPDATE orders SET status=%s WHERE id=%s",
                    ("Cancelled", order_id))
        conn.commit()
        flash("Order cancelled successfully!", "success")
    else:
        flash("Order cannot be cancelled (already approved, rejected or cancelled).", "danger")

    cur.close()
    conn.close()

    return redirect(url_for('view_orders'))

@app.route('/customer/update_profile', methods=['GET', 'POST'])
def update_profile():
    if "customer" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("customer_login"))

    customer_id = session["customer"]["id"]

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Get current profile details
    cur.execute("SELECT name, email, address FROM customers WHERE id=%s", (customer_id,))
    customer = cur.fetchone()

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        address = request.form["address"]
        password = request.form["password"]

        # Update query
        if password.strip() == "":
            # Update without password
            cur.execute("""
                UPDATE customers 
                SET name=%s, email=%s, address=%s 
                WHERE id=%s
            """, (name, email, address, customer_id))
        else:
            # Update with password
            cur.execute("""
                UPDATE customers 
                SET name=%s, email=%s, address=%s, password=%s
                WHERE id=%s
            """, (name, email, address, password, customer_id))

        conn.commit()

        # Update session values
        session["customer"]["name"] = name
        session["customer"]["email"] = email

        flash("Profile updated successfully!", "success")
        return redirect(url_for("customer_dashboard"))

    cur.close()
    conn.close()

    return render_template("update_profile.html", customer=customer)


@app.route("/customer/rate/<int:order_id>", methods=["POST"])
def rate_captain(order_id):
    if "customer" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("customer_login"))

    customer_id = session["customer"]["id"]
    rating = request.form.get("rating")
    review = request.form.get("review", "").strip()  # optional

    if not rating:
        flash("Please provide a rating.", "danger")
        return redirect(url_for("view_orders"))

    conn = get_db_connection()
    cur = conn.cursor()

    # Check if order exists, belongs to customer, and is completed
    cur.execute("""
        SELECT captain_id, status FROM orders
        WHERE id=%s AND customer_id=%s
    """, (order_id, customer_id))
    order = cur.fetchone()

    if not order:
        flash("Order not found.", "danger")
        cur.close()
        conn.close()
        return redirect(url_for("view_orders"))

    captain_id, status = order
    if status != "Completed":
        flash("You can only rate after the service is completed.", "danger")
        cur.close()
        conn.close()
        return redirect(url_for("view_orders"))

    # Insert rating
    cur.execute("""
        INSERT INTO ratings (customer_id, captain_id, order_id, rating, review)
        VALUES (%s, %s, %s, %s, %s)
    """, (customer_id, captain_id, order_id, rating, review))
    conn.commit()
    cur.close()
    conn.close()

    flash("Thank you for rating the Captain!", "success")
    return redirect(url_for("view_orders"))

# ---------------------------
# CAPTAIN MODULE
# ---------------------------
from flask import request, redirect, url_for, flash, render_template
import mysql.connector

@app.route("/captain/register", methods=["GET", "POST"])
def captain_register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        education = request.form.get("education", "").strip()
        experience = request.form.get("experience", "no")
        upi_id = request.form.get("upi_id", "").strip()
        adhar_number = request.form.get("adhar_no", "").strip()
        password = request.form.get("password", "").strip()

        if not (name and phone and password):
            flash("Please fill required fields", "danger")
            return redirect(url_for("captain_register"))

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO captains (name, phone, address, education, experience, password, upi_id, adhar_number)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (name, phone, address, education, experience, password, upi_id, adhar_number))

            conn.commit()
            flash("You have successfully registered!", "success")
            return redirect(url_for("captain_login"))

        except mysql.connector.Error as e:
            conn.rollback()
            flash(f"Error: {e.msg}", "danger")
            return redirect(url_for("captain_register"))
        finally:
            cur.close()
            conn.close()

    return render_template("captain_register.html")


@app.route("/captain/profile")
def captain_profile():
    if "captain" not in session:
        return redirect(url_for("captain_login"))

    captain_id = session["captain"]["id"]
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM captains WHERE id=%s", (captain_id,))
    captain = cur.fetchone()
    cur.execute("""
        SELECT sk.name FROM captain_skills cs
        JOIN skills sk ON cs.skill_id = sk.id
        WHERE cs.captain_id=%s
    """, (captain_id,))
    skills = [s["name"] for s in cur.fetchall()]
    cur.close(); conn.close()
    return render_template("captain_profile.html", captain=captain, skills=skills)

@app.route("/captain/messages/<int:order_id>", methods=["GET","POST"])
def captain_messages(order_id):
    if "captain" not in session:
        return redirect(url_for("captain_login"))
    captain_id = session["captain"]["id"]
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    if request.method == "POST":
        msg = request.form.get("message","").strip()
        receiver_id = request.form.get("customer_id")
        cur.execute("INSERT INTO messages (sender_type, sender_id, receiver_type, receiver_id, order_id, body) VALUES (%s,%s,%s,%s,%s,%s)",
                    ("captain", captain_id, "customer", receiver_id, order_id, msg))
        conn.commit()
        flash("Message sent!", "success")

    cur.execute("SELECT * FROM messages WHERE order_id=%s ORDER BY created_at ASC", (order_id,))
    messages = cur.fetchall()
    cur.close(); conn.close()
    return render_template("captain_messages.html", messages=messages, order_id=order_id)


@app.route("/captain/login", methods=["GET","POST"])
def captain_login():
    if request.method == "POST":
        phone = request.form.get("phone","").strip()
        password = request.form.get("password","").strip()

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM captains WHERE phone=%s AND password=%s", (phone, password))
        captain = cur.fetchone()
        cur.close()
        conn.close()

        if captain:
            session["captain"] = {
                "id": captain["id"],
                "name": captain["name"],
                "phone": captain["phone"]
            }

            flash("Login successful!", "success")
            return redirect(url_for("captain_dashboard"))

        flash("Invalid phone or password", "danger")
        return redirect(url_for("captain_login"))

    return render_template("captain_login.html")




@app.route("/captain/dashboard")
def captain_dashboard():
    if "captain" not in session:
        return redirect("/captain/login")

    cap_id = session["captain"]["id"]

    conn = get_db_connection()

    try:
        # Orders assigned to this captain or unassigned
        cur_orders = conn.cursor(dictionary=True, buffered=True)
        cur_orders.execute("""
            SELECT 
                o.id AS order_id,
                c.name AS customer_name,
                s.name AS service_name,
                s.price AS total_amount,
                o.order_date,
                o.status,
                o.captain_id
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            JOIN services s ON o.service_id = s.id
            WHERE o.captain_id IS NULL OR o.captain_id = %s
            ORDER BY o.order_date DESC
        """, (cap_id,))
        orders = cur_orders.fetchall()
        cur_orders.close()

        # Total completed
        cur_completed = conn.cursor(dictionary=True, buffered=True)
        cur_completed.execute(
            "SELECT COUNT(*) AS total FROM orders WHERE captain_id=%s AND status='Completed'",
            (cap_id,)
        )
        total_completed = cur_completed.fetchone()["total"] or 0
        cur_completed.close()

        # Total earned from captain_earnings
        cur_earnings = conn.cursor(dictionary=True, buffered=True)
        cur_earnings.execute(
            "SELECT SUM(amount) AS earned FROM captain_earnings WHERE captain_id=%s",
            (cap_id,)
        )
        earned = cur_earnings.fetchone()["earned"] or 0
        cur_earnings.close()

        # Average rating from ratings table
        cur_rating = conn.cursor(dictionary=True, buffered=True)
        cur_rating.execute(
            "SELECT AVG(rating) AS avg_rating FROM ratings WHERE captain_id=%s",
            (cap_id,)
        )
        avg_rating = cur_rating.fetchone()["avg_rating"] or 0
        cur_rating.close()

    finally:
        conn.close()

    return render_template(
        "captain_dashboard.html",
        orders=orders,
        total_completed=total_completed,
        earned=earned,
        avg_rating=round(avg_rating, 1)
    )




@app.route("/captain/accept/<int:order_id>", methods=["POST"])  # should be POST
def captain_accept(order_id):
    if "captain" not in session:
        return redirect("/captain/login")

    captain_id = session["captain"]["id"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        UPDATE orders 
        SET captain_id = %s, status='Accepted'
        WHERE id = %s AND captain_id IS NULL
    """, (captain_id, order_id))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect("/captain/dashboard")



@app.route('/captain/complete/<int:order_id>', methods=['POST'])
def complete_order(order_id):
    if "captain" not in session:
        return redirect("/captain/login")

    captain_id = session['captain']['id']

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Fetch order price
    cur.execute("""
        SELECT s.price
        FROM orders o
        JOIN services s ON o.service_id = s.id
        WHERE o.id = %s AND o.captain_id = %s
    """, (order_id, captain_id))

    service = cur.fetchone()
    if not service:
        flash("Order not found or not assigned to you", "danger")
        return redirect("/captain/dashboard")

    amount = service['price']

    # Update order as completed
    cur.execute("""
        UPDATE orders
        SET status='Completed',
            total_amount=%s,
            captain_completed_at=NOW()
        WHERE id=%s AND captain_id=%s
    """, (amount, order_id, captain_id))

    # Update captain earnings
    cur.execute("""
        INSERT INTO captain_earnings (captain_id, order_id, amount)
        VALUES (%s, %s, %s)
    """, (captain_id, order_id, amount))

    conn.commit()
    cur.close()
    conn.close()

    flash("Order completed successfully!", "success")
    return redirect("/captain/dashboard")



# ---------------------------
# ADMIN MODULE
# ---------------------------
# ---------------------------
# ADMIN MODULE
# ---------------------------

# Admin login
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM admins WHERE email=%s", (username,))
        admin = cur.fetchone()
        cur.close(); conn.close()
        if admin and admin["password"] == password:
            session["admin"] = {"id": admin["id"], "name": admin["name"], "email": admin["email"]}
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin credentials", "danger")
    return render_template("admin_login.html")


# Admin logout
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    flash("Logged out", "info")
    return redirect(url_for("admin_login"))


# Admin dashboard
@app.route("/admin/dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) as total_customers FROM customers")
    total_customers = cur.fetchone()["total_customers"]
    cur.execute("SELECT COUNT(*) as total_captains FROM captains")
    total_captains = cur.fetchone()["total_captains"]
    cur.execute("SELECT COUNT(*) as total_orders FROM orders")
    total_orders = cur.fetchone()["total_orders"]
    cur.close(); conn.close()
    return render_template("admin_dashboard.html",
                           total_customers=total_customers,
                           total_captains=total_captains,
                           total_orders=total_orders)


# ---------------------------
# Manage Captains
# ---------------------------
@app.route("/admin/captains")
def admin_captains():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True, buffered=True)

    # Main captain list
    cur.execute("""
        SELECT c.*, s.name AS service_name
        FROM captains c
        LEFT JOIN services s ON c.service_id = s.id
        ORDER BY c.created_at DESC
    """)
    captains = cur.fetchall()

    # Calculate average rating for each captain
    for cap in captains:
        cur.execute("""
            SELECT AVG(r.rating) AS avg_rating
            FROM ratings r
            WHERE r.captain_id=%s
        """, (cap["id"],))
        cap["avg_rating"] = round(cur.fetchone()['avg_rating'] or 0, 1)

    cur.close()
    conn.close()

    return render_template("admin_captains.html", captains=captains)



# Approve / Reject / Fire captain
@app.route("/admin/captain/<int:cid>/update", methods=["POST"])
def admin_update_captain(cid):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    action = request.form.get("action")
    conn = get_db_connection()
    cur = conn.cursor()

    if action == "approve":
        cur.execute("UPDATE captains SET status=%s WHERE id=%s", ("approved", cid))
    elif action == "reject":
        cur.execute("UPDATE captains SET status=%s WHERE id=%s", ("rejected", cid))
    elif action == "fire":
        cur.execute("UPDATE captains SET status=%s WHERE id=%s", ("fired", cid))
    elif action == "delete":
        # Delete related earnings first
        cur.execute("DELETE FROM captain_earnings WHERE captain_id=%s", (cid,))
        # Now delete the captain
        cur.execute("DELETE FROM captains WHERE id=%s", (cid,))

    else:
        flash("Invalid action.", "danger")

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("admin_captains"))  # make sure this points to your captain listing page



# Message Captain
@app.route("/admin/message/captain", methods=["POST"])
def admin_message_captain():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    captain_id = request.form.get("captain_id")
    body = request.form.get("body", "").strip()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO messages (sender_type, sender_id, receiver_type, receiver_id, body)
        VALUES (%s,%s,%s,%s,%s)
    """, ("admin", session["admin"]["id"], "captain", captain_id, body))
    conn.commit(); cur.close(); conn.close()
    flash("Message sent to captain.", "success")
    return redirect(url_for("admin_captains"))


# ---------------------------
# Manage Customers
# ---------------------------
@app.route("/admin/customers")
def admin_customers():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM customers")
    customers = cur.fetchall()
    cur.close(); conn.close()
    return render_template("admin_customers.html", customers=customers)


@app.route("/admin/customer/<int:cid>/delete", methods=["POST"])
def admin_delete_customer(cid):
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM customers WHERE id=%s", (cid,))
    conn.commit(); cur.close(); conn.close()
    flash("Customer deleted.", "info")
    return redirect(url_for("admin_customers"))


# ---------------------------
# Manage Orders
# ---------------------------
@app.route("/admin/orders")
def admin_orders():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT o.*, s.name as service_name, c.name as customer_name, cap.name as captain_name
        FROM orders o
        LEFT JOIN services s ON o.service_id = s.id
        LEFT JOIN customers c ON o.customer_id = c.id
        LEFT JOIN captains cap ON o.captain_id = cap.id
        ORDER BY o.order_date DESC
    """)
    orders = cur.fetchall()
    cur.close(); conn.close()
    return render_template("admin_orders.html", orders=orders)


# Optional: mark order as completed or assign captain
@app.route("/admin/order/<int:oid>/update", methods=["POST"])
def admin_update_order(oid):
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    status = request.form.get("status")
    captain_id = request.form.get("captain_id")
    conn = get_db_connection()
    cur = conn.cursor()
    if status:
        cur.execute("UPDATE orders SET status=%s WHERE id=%s", (status, oid))
    if captain_id:
        cur.execute("UPDATE orders SET captain_id=%s WHERE id=%s", (captain_id, oid))
    conn.commit(); cur.close(); conn.close()
    flash("Order updated.", "success")
    return redirect(url_for("admin_orders"))


# ---------------------------
# Manage Services
# ---------------------------
@app.route("/admin/services")
def admin_services():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM services ORDER BY ID ASC")
    services = cur.fetchall()
    cur.close(); conn.close()
    return render_template("admin_services.html", services=services)


@app.route("/admin/service/add", methods=["POST"])
def admin_add_service():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    name = request.form.get("name").strip()
    price = request.form.get("price")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO services (name, price) VALUES (%s, %s)", (name, price))
    conn.commit(); cur.close(); conn.close()
    flash("Service added.", "success")
    return redirect(url_for("admin_services"))


@app.route("/admin/service/<int:sid>/edit", methods=["POST"])
def admin_edit_service(sid):
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    name = request.form.get("name").strip()
    price = request.form.get("price")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE services SET name=%s, price=%s WHERE id=%s", (name, price, sid))
    conn.commit(); cur.close(); conn.close()
    flash("Service updated.", "success")
    return redirect(url_for("admin_services"))


@app.route("/admin/service/<int:sid>/delete", methods=["POST"])
def admin_delete_service(sid):
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM services WHERE id=%s", (sid,))
    conn.commit(); cur.close(); conn.close()
    flash("Service deleted.", "info")
    return redirect(url_for("admin_services"))


# ---------------------------
# Run the App
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)