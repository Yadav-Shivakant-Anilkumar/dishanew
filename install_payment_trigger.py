"""
Install the payment trigger in the database
This script will install the trigger that automatically updates fees when payments are made
"""
from database import get_db_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def install_trigger():
    """Install the update_fees_on_payment trigger"""
    connection = get_db_connection()
    if not connection:
        logger.error("Failed to connect to database")
        return False
    
    cursor = None
    try:
        cursor = connection.cursor()
        
        # First, check if trigger already exists
        cursor.execute("""
            SELECT TRIGGER_NAME 
            FROM information_schema.TRIGGERS 
            WHERE TRIGGER_SCHEMA = DATABASE() 
            AND TRIGGER_NAME = 'update_fees_on_payment'
        """)
        
        existing = cursor.fetchone()
        
        if existing:
            logger.info("Trigger 'update_fees_on_payment' already exists. Dropping it first...")
            cursor.execute("DROP TRIGGER IF EXISTS update_fees_on_payment")
            connection.commit()
        
        # Now create the trigger
        logger.info("Installing trigger 'update_fees_on_payment'...")
        
        trigger_sql = """
CREATE TRIGGER update_fees_on_payment
AFTER INSERT ON fee_transactions
FOR EACH ROW
BEGIN
    DECLARE new_paid DECIMAL(10, 2);
    DECLARE new_due DECIMAL(10, 2);
    DECLARE total DECIMAL(10, 2);
    DECLARE new_status VARCHAR(20);
    
    -- Get total amount for this fee
    SELECT total_amount INTO total
    FROM fees
    WHERE fee_id = NEW.fee_id;
    
    -- Calculate new paid amount (sum of all transactions)
    SELECT COALESCE(SUM(amount), 0) INTO new_paid
    FROM fee_transactions
    WHERE fee_id = NEW.fee_id;
    
    -- Calculate new due amount
    SET new_due = total - new_paid;
    
    -- Ensure due amount is not negative
    IF new_due < 0 THEN
        SET new_due = 0;
    END IF;
    
    -- Determine payment status
    IF new_due = 0 THEN
        SET new_status = 'paid';
    ELSEIF new_paid > 0 THEN
        SET new_status = 'partial';
    ELSE
        SET new_status = 'pending';
    END IF;
    
    -- Update the fees record
    UPDATE fees
    SET paid_amount = new_paid,
        due_amount = new_due,
        payment_status = new_status,
        updated_at = CURRENT_TIMESTAMP
    WHERE fee_id = NEW.fee_id;
END
        """
        
        cursor.execute(trigger_sql)
        connection.commit()
        
        # Verify installation
        cursor.execute("""
            SELECT TRIGGER_NAME, EVENT_MANIPULATION, ACTION_TIMING
            FROM information_schema.TRIGGERS 
            WHERE TRIGGER_SCHEMA = DATABASE() 
            AND TRIGGER_NAME = 'update_fees_on_payment'
        """)
        
        result = cursor.fetchone()
        
        if result:
            logger.info(f"✅ Trigger installed successfully!")
            logger.info(f"   Trigger: {result[0]}")
            logger.info(f"   Event: {result[1]}")
            logger.info(f"   Timing: {result[2]}")
            return True
        else:
            logger.error("❌ Trigger installation failed - could not verify")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error installing trigger: {e}")
        if connection:
            connection.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == "__main__":
    print("=" * 80)
    print("INSTALLING PAYMENT TRIGGER")
    print("=" * 80)
    print()
    
    success = install_trigger()
    
    print()
    print("=" * 80)
    if success:
        print("✅ INSTALLATION COMPLETE")
        print()
        print("Next step: Run 'python fix_payment_data.py' to sync existing payment data")
    else:
        print("❌ INSTALLATION FAILED")
        print()
        print("Please check the error messages above and try again")
    print("=" * 80)
