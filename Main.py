import mysql.connector
from Customer import customer_menu, register_customer, login_customer
from Admin import login_admin


# Database connection setup
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",  # Change to your MySQL username
        password="Snehaal@123",  # Change to your MySQL password
        database="vcube"
    )

def main():

    while True:
        print("\n--- Servizo ---")
        print("1. Admin Login")
        print("2. Customer Registration")
        print("3. Customer Login")
        print("4. Exit")
        choice = input("Enter your choice: ").strip()

        if choice == '1':
            login_admin()
        elif choice == '2':
            register_customer()
        elif choice == '3':
            customer = login_customer()
            if customer:
                customer_menu(customer)
        elif choice == '4':
            break
        else:
            print("Invalid choice. Try again.")


if __name__ == "__main__":
    main()
