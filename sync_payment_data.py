"""
Data Synchronization Script
This script fixes payment mismatches by synchronizing fee_transactions with fees table
"""
from database import execute_query, get_db_connection
from datetime import datetime

print("=" * 80)
print("PAYMENT DATA SYNCHRONIZATION SCRIPT")
print("=" * 80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# First, let's see the current state
print("STEP 1: Checking for mismatches...")
print("-" * 80)

mismatches = execute_query("""
    SELECT 
        f.fee_id,
        f.student_id,
        s.enrollment_no,
        u.full_name,
        c.course_name,
        f.total_amount,
        f.paid_amount as current_paid,
        COALESCE(SUM(ft.amount), 0) as actual_paid,
        f.due_amount as current_due,
        (f.total_amount - COALESCE(SUM(ft.amount), 0)) as actual_due,
        f.payment_status as current_status
    FROM fees f
    JOIN courses c ON f.course_id = c.course_id
    JOIN students s ON f.student_id = s.student_id
    JOIN users u ON s.user_id = u.user_id
    LEFT JOIN fee_transactions ft ON f.fee_id = ft.fee_id
    GROUP BY f.fee_id
    HAVING current_paid != actual_paid OR current_due != actual_due
""", fetch=True)

if not mismatches:
    print("✅ No mismatches found. All data is synchronized!")
    print("\n" + "=" * 80)
    exit(0)

print(f"⚠️ Found {len(mismatches)} mismatch(es):\n")
for m in mismatches:
    print(f"Fee ID {m['fee_id']} - {m['full_name']} ({m['enrollment_no']})")
    print(f"  Course: {m['course_name']}")
    print(f"  Current: Paid=₹{m['current_paid']}, Due=₹{m['current_due']}, Status={m['current_status']}")
    print(f"  Actual:  Paid=₹{m['actual_paid']}, Due=₹{m['actual_due']}")
    print()

# Ask for confirmation
response = input("\nDo you want to synchronize these records? (yes/no): ").strip().lower()
if response != 'yes':
    print("❌ Synchronization cancelled.")
    exit(0)

print("\nSTEP 2: Synchronizing data...")
print("-" * 80)

connection = get_db_connection()
if not connection:
    print("❌ Failed to connect to database!")
    exit(1)

cursor = connection.cursor(dictionary=True)
fixed_count = 0

try:
    for m in mismatches:
        new_paid = float(m['actual_paid'])
        new_due = float(m['actual_due'])
        
        # Determine new status
        if new_due <= 0:
            new_status = 'paid'
        elif new_paid > 0:
            new_status = 'partial'
        else:
            new_status = 'pending'
        
        # Update the record
        cursor.execute("""
            UPDATE fees
            SET paid_amount = %s,
                due_amount = %s,
                payment_status = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE fee_id = %s
        """, (new_paid, new_due, new_status, m['fee_id']))
        
        print(f"✅ Fixed Fee ID {m['fee_id']} - {m['full_name']}")
        print(f"   Updated: Paid=₹{new_paid}, Due=₹{new_due}, Status={new_status}")
        fixed_count += 1
    
    # Commit all changes
    connection.commit()
    
    print(f"\n✅ Successfully synchronized {fixed_count} record(s)!")
    
except Exception as e:
    connection.rollback()
    print(f"\n❌ Error during synchronization: {e}")
    print("All changes have been rolled back.")
    
finally:
    cursor.close()
    connection.close()

print("\n" + "=" * 80)
print("SYNCHRONIZATION COMPLETE")
print("=" * 80)
