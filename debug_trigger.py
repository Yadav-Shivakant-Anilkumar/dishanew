"""
Debug why the trigger is not working
"""
from database import execute_query

print("=" * 80)
print("TRIGGER DEBUG INVESTIGATION")
print("=" * 80)

# 1. Check if trigger exists
print("\n1. Checking trigger installation...")
trigger_check = execute_query("""
    SELECT TRIGGER_NAME, EVENT_MANIPULATION, ACTION_TIMING, EVENT_OBJECT_TABLE
    FROM information_schema.TRIGGERS 
    WHERE TRIGGER_SCHEMA = DATABASE() 
    AND TRIGGER_NAME = 'update_fees_on_payment'
""", fetch_one=True)

if trigger_check:
    print(f"✅ Trigger exists: {trigger_check['TRIGGER_NAME']}")
    print(f"   Table: {trigger_check['EVENT_OBJECT_TABLE']}")
    print(f"   Timing: {trigger_check['ACTION_TIMING']} {trigger_check['EVENT_MANIPULATION']}")
else:
    print("❌ Trigger NOT found!")

# 2. Check recent transactions
print("\n2. Recent Transactions:")
transactions = execute_query("""
    SELECT transaction_id, fee_id, amount, payment_date, payment_method, receipt_no
    FROM fee_transactions
    ORDER BY transaction_id DESC
    LIMIT 5
""", fetch=True)

if transactions:
    for t in transactions:
        print(f"\nTransaction ID: {t['transaction_id']}")
        print(f"  Fee ID: {t['fee_id']}")
        print(f"  Amount: ₹{t['amount']}")
        print(f"  Method: {t['payment_method']}")
        print(f"  Receipt: {t['receipt_no']}")
        
        # Check corresponding fee record
        fee = execute_query(
            "SELECT * FROM fees WHERE fee_id = %s",
            (t['fee_id'],),
            fetch_one=True
        )
        
        if fee:
            print(f"  Fee Record:")
            print(f"    Total: ₹{fee['total_amount']}")
            print(f"    Paid: ₹{fee['paid_amount']}")
            print(f"    Due: ₹{fee['due_amount']}")
            print(f"    Status: {fee['payment_status']}")
            
            # Calculate what it SHOULD be
            actual_paid = execute_query(
                "SELECT COALESCE(SUM(amount), 0) as total FROM fee_transactions WHERE fee_id = %s",
                (t['fee_id'],),
                fetch_one=True
            )['total']
            
            if float(fee['paid_amount']) != float(actual_paid):
                print(f"    ❌ MISMATCH! Should be ₹{actual_paid}")
            else:
                print(f"    ✅ Correct")

# 3. Check trigger definition
print("\n3. Checking trigger definition...")
trigger_def = execute_query("""
    SELECT ACTION_STATEMENT
    FROM information_schema.TRIGGERS 
    WHERE TRIGGER_SCHEMA = DATABASE() 
    AND TRIGGER_NAME = 'update_fees_on_payment'
""", fetch_one=True)

if trigger_def:
    print("Trigger SQL:")
    print(trigger_def['ACTION_STATEMENT'][:500] + "...")  # First 500 chars

# 4. Try manual trigger execution
print("\n4. Testing manual fee_update for fee_id = 5...")
fee_id_to_test = 5

# Get current fee status
fee_before = execute_query(
    "SELECT * FROM fees WHERE fee_id = %s",
    (fee_id_to_test,),
    fetch_one=True
)

if fee_before:
    print(f"\nBEFORE manual update:")
    print(f"  Paid: ₹{fee_before['paid_amount']}")
    print(f"  Due: ₹{fee_before['due_amount']}")
    print(f"  Status: {fee_before['payment_status']}")
    
    # Calculate correct values
    actual_paid = execute_query(
        "SELECT COALESCE(SUM(amount), 0) as total FROM fee_transactions WHERE fee_id = %s",
        (fee_id_to_test,),
        fetch_one=True
    )['total']
    
    new_due = float(fee_before['total_amount']) - float(actual_paid)
    if new_due < 0:
        new_due = 0
        
    if new_due == 0:
        new_status = 'paid'
    elif actual_paid > 0:
        new_status = 'partial'
    else:
        new_status = 'pending'
    
    print(f"\n  Should be:")
    print(f"    Paid: ₹{actual_paid}")
    print(f"    Due: ₹{new_due}")
    print(f"    Status: {new_status}")
    
    # Manually update
    execute_query(
        """UPDATE fees SET paid_amount = %s, due_amount = %s,
           payment_status = %s WHERE fee_id = %s""",
        (actual_paid, new_due, new_status, fee_id_to_test),
        commit=True
    )
    
    # Check after
    fee_after = execute_query(
        "SELECT * FROM fees WHERE fee_id = %s",
        (fee_id_to_test,),
        fetch_one=True
    )
    
    print(f"\nAFTER manual update:")
    print(f"  Paid: ₹{fee_after['paid_amount']}")
    print(f"  Due: ₹{fee_after['due_amount']}")
    print(f"  Status: {fee_after['payment_status']}")
    print("  ✅ Manual update successful!")

print("\n" + "=" * 80)
print("END DEBUG")
print("=" * 80)
