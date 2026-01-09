"""
Script to investigate payment update issues
"""
from database import execute_query
from datetime import datetime

print("=" * 80)
print("PAYMENT ISSUE INVESTIGATION REPORT")
print("=" * 80)
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# 1. Check fee_transactions table
print("1. RECENT FEE TRANSACTIONS")
print("-" * 80)
transactions = execute_query("""
    SELECT ft.*, f.student_id, c.course_name
    FROM fee_transactions ft
    JOIN fees f ON ft.fee_id = f.fee_id
    JOIN courses c ON f.course_id = c.course_id
    ORDER BY ft.transaction_id DESC
    LIMIT 10
""", fetch=True)

if transactions:
    for t in transactions:
        print(f"Transaction ID: {t['transaction_id']}")
        print(f"  Receipt: {t['receipt_no']}")
        print(f"  Student ID: {t['student_id']}")
        print(f"  Course: {t['course_name']}")
        print(f"  Amount: ₹{t['amount']}")
        print(f"  Date: {t['payment_date']}")
        print(f"  Method: {t['payment_method']}")
        print(f"  Fee ID: {t['fee_id']}")
        print()
else:
    print("No transactions found!\n")

# 2. Check fees table
print("2. FEE RECORDS")
print("-" * 80)
fees = execute_query("""
    SELECT f.*, c.course_name, s.enrollment_no, u.full_name
    FROM fees f
    JOIN courses c ON f.course_id = c.course_id
    JOIN students s ON f.student_id = s.student_id
    JOIN users u ON s.user_id = u.user_id
    ORDER BY f.fee_id DESC
    LIMIT 10
""", fetch=True)

if fees:
    for fee in fees:
        print(f"Fee ID: {fee['fee_id']}")
        print(f"  Student: {fee['full_name']} ({fee['enrollment_no']})")
        print(f"  Course: {fee['course_name']}")
        print(f"  Total: ₹{fee['total_amount']}")
        print(f"  Paid: ₹{fee['paid_amount']}")
        print(f"  Due: ₹{fee['due_amount']}")
        print(f"  Status: {fee['payment_status']}")
        print()
else:
    print("No fee records found!\n")

# 3. Cross-check: Find transactions without corresponding fee updates
print("3. PAYMENT MISMATCH ANALYSIS")
print("-" * 80)
mismatch = execute_query("""
    SELECT 
        f.fee_id,
        f.student_id,
        c.course_name,
        f.total_amount,
        f.paid_amount as recorded_paid,
        COALESCE(SUM(ft.amount), 0) as actual_payments,
        f.due_amount as recorded_due,
        (f.total_amount - COALESCE(SUM(ft.amount), 0)) as actual_due,
        f.payment_status
    FROM fees f
    JOIN courses c ON f.course_id = c.course_id
    LEFT JOIN fee_transactions ft ON f.fee_id = ft.fee_id
    GROUP BY f.fee_id
    HAVING recorded_paid != actual_payments OR recorded_due != actual_due
""", fetch=True)

if mismatch:
    print("⚠️ FOUND MISMATCHES! Payment data is out of sync!\n")
    for m in mismatch:
        print(f"Fee ID: {m['fee_id']} | Student ID: {m['student_id']}")
        print(f"  Course: {m['course_name']}")
        print(f"  Total Amount: ₹{m['total_amount']}")
        print(f"  Recorded Paid: ₹{m['recorded_paid']} | Actual Payments: ₹{m['actual_payments']} {'❌ MISMATCH' if m['recorded_paid'] != m['actual_payments'] else '✓'}")
        print(f"  Recorded Due: ₹{m['recorded_due']} | Actual Due: ₹{m['actual_due']} {'❌ MISMATCH' if m['recorded_due'] != m['actual_due'] else '✓'}")
        print(f"  Payment Status: {m['payment_status']}")
        print()
else:
    print("✓ No mismatches found. All payment records are synchronized.\n")

# 4. Check specific student from the screenshot (receipt RCP20263773472971)
print("4. SPECIFIC RECEIPT ANALYSIS (RCP20263773472971)")
print("-" * 80)
specific = execute_query("""
    SELECT 
        ft.*,
        f.fee_id,
        f.student_id,
        f.total_amount,
        f.paid_amount,
        f.due_amount,
        f.payment_status,
        c.course_name,
        s.enrollment_no,
        u.full_name
    FROM fee_transactions ft
    JOIN fees f ON ft.fee_id = f.fee_id
    JOIN courses c ON f.course_id = c.course_id
    JOIN students s ON f.student_id = s.student_id
    JOIN users u ON s.user_id = u.user_id
    WHERE ft.receipt_no = 'RCP20263773472971'
""", fetch_one=True)

if specific:
    print(f"✓ Receipt Found!")
    print(f"Student: {specific['full_name']} ({specific['enrollment_no']})")
    print(f"Course: {specific['course_name']}")
    print(f"Payment Amount: ₹{specific['amount']}")
    print(f"Payment Date: {specific['payment_date']}")
    print(f"Payment Method: {specific['payment_method']}")
    print()
    print(f"Fee Record Status:")
    print(f"  Fee ID: {specific['fee_id']}")
    print(f"  Total: ₹{specific['total_amount']}")
    print(f"  Paid: ₹{specific['paid_amount']}")
    print(f"  Due: ₹{specific['due_amount']}")
    print(f"  Status: {specific['payment_status']}")
    print()
    
    if specific['paid_amount'] == 0:
        print("❌ PROBLEM IDENTIFIED: Payment recorded in transactions but NOT updated in fees table!")
    elif specific['paid_amount'] != specific['amount']:
        print(f"⚠️ WARNING: Paid amount (₹{specific['paid_amount']}) doesn't match transaction (₹{specific['amount']})")
    else:
        print("✓ Payment properly recorded in both tables")
else:
    print("❌ Receipt not found in database!")

print("\n" + "=" * 80)
print("END OF REPORT")
print("=" * 80)
