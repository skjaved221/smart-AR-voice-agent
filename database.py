import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "accounts_receivable.db")

def get_connection():
    """Returns a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initializes the database schema and loads mock data."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create the invoices table
    print("Creating 'invoices' table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            invoice_id TEXT PRIMARY KEY,
            customer_name TEXT NOT NULL,
            amount_due REAL NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)
    
    # Populate with mock data for testing
    mock_invoices = [
        ("INV-2026-001", "Acme Corporation", 4500.50, "June 1, 2026", "OVERDUE"),
        ("INV-2026-002", "Stark Industries", 12500.00, "June 12, 2026", "OVERDUE"),
        ("INV-2026-003", "Wayne Enterprises", 980.00, "July 5, 2026", "PENDING")
    ]
    
    print("Inserting mock invoice records...")
    cursor.executemany("""
        INSERT OR REPLACE INTO invoices (invoice_id, customer_name, amount_due, due_date, status)
        VALUES (?, ?, ?, ?, ?)
    """, mock_invoices)
    
    conn.commit()
    conn.close()
    print(f"Database initialized successfully at: {DB_PATH}\n")

def get_invoice_details(invoice_id):
    """Retrieves invoice data as a dictionary by its invoice ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT invoice_id, customer_name, amount_due, due_date, status 
        FROM invoices 
        WHERE invoice_id = ?
    """, (invoice_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "invoice_id": row[0],
            "customer_name": row[1],
            "amount_due": row[2],
            "due_date": row[3],
            "status": row[4]
        }
    return None

def update_invoice_status(invoice_id, new_status):
    """Updates the status of an invoice (e.g., to 'PAID' or 'PROMISED')."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE invoices 
        SET status = ? 
        WHERE invoice_id = ?
    """, (new_status, invoice_id))
    conn.commit()
    conn.close()
    print(f"Invoice {invoice_id} status updated to: {new_status}")

if __name__ == "__main__":
    init_db()
    
    # Test lookup function
    test_id = "INV-2026-001"
    details = get_invoice_details(test_id)
    print(f"Testing lookup for {test_id}:")
    print(details)
