from helpers import get_db_connection
from tabulate import tabulate


#Admin Login
def login_admin():
    conn = get_db_connection()
    cursor = conn.cursor()

    email = input("Enter admin email: ")

    # Step 1: Check if email exists
    cursor.execute("SELECT id, password FROM admins WHERE email=%s", (email,))
    result = cursor.fetchone()

    if not result:
        print("No admin found with this email.")
        conn.close()
        return

    admin_id, correct_password = result

    # Step 2: Ask for password
    password = input("Enter admin password: ")

    if password == correct_password:
        print("Admin login successful.")
        conn.close()
        admin_menu()
    else:
        print("Invalid password.")
        conn.close()

# Admin functions
def admin_menu():
    while True:
        print("\n--- Admin Menu ---")
        print("1. Add Service")
        print("2. View Services")
        print("3. Delete Service")      # Delete option
        print("4. Edit Service")        # New edit option
        print("5. View Customers")
        print("6. Delete Customers")
        print("7. View Orders")
        print("8. Logout")
        choice = input("Enter your choice: ")

        if choice == '1':
            add_service()
        elif choice == '2':
            admin_view_services()
        elif choice == '3':
            delete_service()
        elif choice == '4':
            edit_service()
        elif choice == '5':
            view_customers_admin()
        elif choice == '6':
            delete_customer()
        elif choice == '7':
            view_customers_admin()
        elif choice == '8':
            print("You have Logged Out!!")
            break
        else:
            print("Invalid choice. Try again.")


def add_service():
    conn = get_db_connection()
    cursor = conn.cursor()
    name = input("Enter service name: ")
    description = input("Enter service description: ")
    price = float(input("Enter price: "))
    cursor.execute("INSERT INTO services (name, description, price) VALUES (%s, %s, %s)", (name, description, price))
    conn.commit()
    conn.close()
    print("Service added successfully.")


def admin_view_services():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM services")
    services = cursor.fetchall()
    conn.close()

    if not services:
        print("No services found.")
        return

    table = []
    for s in services:
        table.append([s['id'], s['name'], s['price'], s['description']])

    headers = ["ID", "Service Name", "Price", "Description"]
    print("\n--- Service List ---")
    print(tabulate(table, headers, tablefmt="grid"))

# Delete Service
def delete_service():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM services")
    services = cursor.fetchall()

    if not services:
        print("No services available to delete.")
        conn.close()
        return

    print("\nAvailable Services:")
    for s in services:
        print(f"{s[0]}. {s[1]}")

    try:
        service_id = int(input("Enter Service ID to delete: "))

        # Confirmation
        confirm = input(f"Are you sure you want to delete service ID {service_id}? (Y/N): ").strip().upper()
        if confirm != 'Y':
            print("Deletion cancelled.")
            conn.close()
            return

        cursor.execute("DELETE FROM services WHERE id=%s", (service_id,))
        conn.commit()
        print("Service deleted successfully.")
    except Exception as e:
        print("Error deleting service:", e)

    conn.close()

# Edit Service
def edit_service():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, price FROM services")
    services = cursor.fetchall()

    if not services:
        print("No services available to edit.")
        conn.close()
        return

    print("\nAvailable Services:")
    for s in services:
        print(f"{s[0]}. {s[1]} - Price: {s[2]}")

    try:
        service_id = int(input("Enter Service ID to edit: "))

        # Get current details
        cursor.execute("SELECT name, price, description FROM services WHERE id=%s", (service_id,))
        service = cursor.fetchone()
        if not service:
            print("Service ID not found.")
            conn.close()
            return

        print(f"Current name: {service[0]}")
        new_name = input("Enter new name (leave blank to keep current): ")
        new_name = new_name if new_name.strip() != "" else service[0]

        print(f"Current description: {service[2]}")
        new_description = input("Enter new description (leave blank to keep current): ")
        new_description = new_description if new_description.strip() != "" else service[2]

        print(f"Current price: {service[1]}")
        new_price_input = input("Enter new price (leave blank to keep current): ")
        new_price = float(new_price_input) if new_price_input.strip() != "" else service[1]

        cursor.execute(
            "UPDATE services SET name=%s, description=%s, price=%s WHERE id=%s",
            (new_name, new_description, new_price, service_id)
        )
        conn.commit()
        print("Service updated successfully.")
    except Exception as e:
        print("Error editing service:", e)

    conn.close()


# View Customers
def view_customers_admin():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM customers")
    customers = cursor.fetchall()
    conn.close()

    if not customers:
        print("No customers found.")
        return

    table = []
    for c in customers:
        table.append([
            c['id'], c['name'], c['email'], c['phone'], c['address'],
            c['community_type'], c['community_name'], c['block_or_house']
        ])

    headers = ["ID", "Name", "Email", "Phone", "Address", "Community Type", "Community/Apartment", "Block/House"]
    print("\n--- Customer Details ---")
    print(tabulate(table, headers, tablefmt="grid"))


#Delete Customers
def delete_customer():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    print("\n--- Delete Customer ---")
    identifier = input("Enter the customer's Email or Phone Number to delete: ").strip()

    # Find the customer first
    if "@" in identifier and "." in identifier:
        cursor.execute("SELECT id, name, email, phone FROM customers WHERE email=%s", (identifier,))
    else:
        cursor.execute("SELECT id, name, email, phone FROM customers WHERE phone=%s", (identifier,))

    customer = cursor.fetchone()

    if not customer:
        print("❌ Customer not found.")
        conn.close()
        return

    # Show customer info before deletion
    print("\nCustomer found:")
    print(tabulate([[customer['id'], customer['name'], customer['email'], customer['phone']]],
                   headers=["ID", "Name", "Email", "Phone"], tablefmt="fancy_grid"))

    confirm = input("Are you sure you want to delete this customer? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("❌ Deletion cancelled.")
        conn.close()
        return

    # Delete customer
    try:
        cursor.execute("DELETE FROM customers WHERE id=%s", (customer['id'],))
        conn.commit()
        print(f"✅ Customer {customer['name']} deleted successfully!")
    except Exception as e:
        print("❌ Error while deleting customer:", e)
    finally:
        cursor.close()
        conn.close()

# View Orders

def view_orders_admin():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Join orders with customer and service details
    cursor.execute("""
        SELECT o.id, c.name AS customer_name, c.phone, s.name AS service_name, s.price, o.order_date, o.status
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        JOIN services s ON o.service_id = s.id
        ORDER BY o.order_date DESC
    """)
    orders = cursor.fetchall()
    conn.close()

    if not orders:
        print("No orders found.")
        return

    # Prepare table data
    table = []
    for o in orders:
        table.append([
            o['id'],
            o['customer_name'],
            o['phone'],
            o['service_name'],
            f"₹{o['price']}",
            o['order_date'].strftime("%Y-%m-%d %H:%M:%S"),
            o['status']
        ])

    headers = ["Order ID", "Customer Name", "Phone", "Service", "Price", "Date & Time", "Status"]
    print("\n--- Orders Received ---")
    print(tabulate(table, headers, tablefmt="grid"))