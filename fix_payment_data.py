"""Fix payment data - update fees table based on transactions"""
from database import execute_query

# Get all fee transactions grouped by fee_id
print("Checking payment transactions...\n")

fee_ids = execute_query(
    "SELECT DISTINCT fee_id FROM fee_transactions",
    fetch=True
)

if fee_ids:
    for row in fee_ids:
        fee_id = row['fee_id']
        
        # Calculate total paid for this fee
        total_paid = execute_query(
            "SELECT COALESCE(SUM(amount), 0) as total FROM fee_transactions WHERE fee_id = %s",
            (fee_id,),
            fetch_one=True
        )['total']
        
        # Get fee details
        fee = execute_query(
            "SELECT * FROM fees WHERE fee_id = %s",
            (fee_id,),
            fetch_one=True
        )
        
        if fee:
            print(f"Fee ID: {fee_id}")
            print(f"  Total Amount: ₹{fee['total_amount']}")
            print(f"  Current Paid: ₹{fee['paid_amount']}")
            print(f"  Actual Paid (from transactions): ₹{total_paid}")
            
            # Calculate new values
            new_paid = float(total_paid)
            new_due = float(fee['total_amount']) - new_paid
            if new_due < 0.01:
                new_due = 0.00
            
            # Determine status
            if new_due == 0:
                new_status = 'paid'
            elif new_paid > 0:
                new_status = 'partial'
            else:
                new_status = 'pending'
            
            # Update if needed
            if fee['paid_amount'] != new_paid or fee['due_amount'] != new_due:
                print(f"  -> Updating to: Paid=₹{new_paid}, Due=₹{new_due}, Status={new_status}")
                
                execute_query(
                    """UPDATE fees SET paid_amount = %s, due_amount = %s, 
                       payment_status = %s WHERE fee_id = %s""",
                    (new_paid, new_due, new_status, fee_id),
                    commit=True
                )
                print("  ✅ Updated!\n")
            else:
                print("  ✓ Already correct\n")
else:
    print("No transactions found")

print("\nDone! Fee records are now synchronized with transaction history.")
