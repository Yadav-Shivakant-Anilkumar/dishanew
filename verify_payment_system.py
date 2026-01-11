"""
Verify the payment system is working correctly
This script checks:
1. Trigger installation
2. Data synchronization
3. Payment status accuracy
"""
from database import execute_query
from datetime import datetime

print("=" * 80)
print("PAYMENT SYSTEM VERIFICATION")
print("=" * 80)
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# 1. Verify trigger exists
print("1. CHECKING TRIGGER INSTALLATION")
print("-" * 80)
trigger = execute_query("""
    SELECT TRIGGER_NAME, EVENT_MANIPULATION, ACTION_TIMING, EVENT_OBJECT_TABLE
    FROM information_schema.TRIGGERS 
    WHERE TRIGGER_SCHEMA = DATABASE() 
    AND TRIGGER_NAME = 'update_fees_on_payment'
""", fetch_one=True)

if trigger:
    print(f"✅ Trigger Found: {trigger['TRIGGER_NAME']}")
    print(f"   Table: {trigger['EVENT_OBJECT_TABLE']}")
    print(f"   Event: {trigger['ACTION_TIMING']} {trigger['EVENT_MANIPULATION']}")
    print()
else:
    print("❌ Trigger NOT found!")
    print("   Please run: python install_payment_trigger.py")
    print()

# 2. Check for data synchronization issues
print("2. CHECKING DATA SYNCHRONIZATION")
print("-" * 80)
mismatch = execute_query("""
    SELECT 
        f.fee_id,
        f.student_id,
        c.course_name,
        u.full_name,
        f.total_amount,
        f.paid_amount as recorded_paid,
        COALESCE(SUM(ft.amount), 0) as actual_payments,
        f.due_amount as recorded_due,
        (f.total_amount - COALESCE(SUM(ft.amount), 0)) as actual_due,
        f.payment_status
    FROM fees f
    JOIN courses c ON f.course_id = c.course_id
    JOIN students s ON f.student_id = s.student_id
    JOIN users u ON s.user_id = u.user_id
    LEFT JOIN fee_transactions ft ON f.fee_id = ft.fee_id
    GROUP BY f.fee_id
    HAVING ABS(recorded_paid - actual_payments) > 0.01 OR ABS(recorded_due - actual_due) > 0.01
""", fetch=True)

if mismatch:
    print(f"⚠️ FOUND {len(mismatch)} MISMATCHES! Payment data is out of sync!\n")
    for m in mismatch:
        print(f"Fee ID: {m['fee_id']} | Student: {m['full_name']}")
        print(f"  Course: {m['course_name']}")
        print(f"  Recorded Paid: ₹{m['recorded_paid']:.2f} | Actual: ₹{m['actual_payments']:.2f}")
        print(f"  Recorded Due: ₹{m['recorded_due']:.2f} | Actual: ₹{m['actual_due']:.2f}")
        print()
    print("⚠️ Please run: python fix_payment_data.py")
else:
    print("✅ All payment records are synchronized!\n")

# 3. Fee Summary
print("3. CURRENT FEE SUMMARY")
print("-" * 80)
summary = execute_query("""
    SELECT 
        COUNT(*) as total_fees,
        SUM(total_amount) as total_amount,
        SUM(paid_amount) as total_paid,
        SUM(due_amount) as total_due,
        SUM(CASE WHEN payment_status = 'paid' THEN 1 ELSE 0 END) as fully_paid,
        SUM(CASE WHEN payment_status = 'partial' THEN 1 ELSE 0 END) as partial_paid,
        SUM(CASE WHEN payment_status = 'pending' THEN 1 ELSE 0 END) as pending
    FROM fees
""", fetch_one=True)

if summary:
    print(f"Total Fee Records: {summary['total_fees']}")
    print(f"Total Amount: ₹{summary['total_amount']:,.2f}")
    print(f"Total Paid: ₹{summary['total_paid']:,.2f}")
    print(f"Total Due: ₹{summary['total_due']:,.2f}")
    print()
    print(f"Status Breakdown:")
    print(f"  - Fully Paid: {summary['fully_paid']} records")
    print(f"  - Partially Paid: {summary['partial_paid']} records")
    print(f"  - Pending: {summary['pending']} records")
    print()

# 4. Recent Transactions
print("4. RECENT TRANSACTIONS (Last 5)")
print("-" * 80)
transactions = execute_query("""
    SELECT 
        ft.transaction_id,
        ft.receipt_no,
        ft.amount,
        ft.payment_date,
        ft.payment_method,
        u.full_name as student_name,
        c.course_name,
        f.payment_status
    FROM fee_transactions ft
    JOIN fees f ON ft.fee_id = f.fee_id
    JOIN students s ON f.student_id = s.student_id
    JOIN users u ON s.user_id = u.user_id
    JOIN courses c ON f.course_id = c.course_id
    ORDER BY ft.transaction_id DESC
    LIMIT 5
""", fetch=True)

if transactions:
    for t in transactions:
        print(f"Receipt: {t['receipt_no']} | ₹{t['amount']:.2f}")
        print(f"  Student: {t['student_name']}")
        print(f"  Course: {t['course_name']}")
        print(f"  Date: {t['payment_date']} | Method: {t['payment_method']}")
        print(f"  Fee Status: {t['payment_status']}")
        print()
else:
    print("No transactions found\n")

# Overall Status
print("=" * 80)
if trigger and not mismatch:
    print("✅ PAYMENT SYSTEM IS FULLY OPERATIONAL")
    print()
    print("Next steps:")
    print("  1. Test making a new payment through the web interface")
    print("  2. Verify the fee status updates automatically")
    print("  3. Check admin reports show correct data")
elif trigger and mismatch:
    print("⚠️ TRIGGER INSTALLED BUT DATA NEEDS SYNC")
    print()
    print("Run: python fix_payment_data.py")
else:
    print("❌ PAYMENT SYSTEM NEEDS CONFIGURATION")
    print()
    print("Run: python install_payment_trigger.py")
print("=" * 80)
