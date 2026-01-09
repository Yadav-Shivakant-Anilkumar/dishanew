-- Database Trigger to Automatically Update Fees Table
-- This trigger ensures that whenever a payment is recorded in fee_transactions,
-- the corresponding fees record is automatically updated

-- Drop trigger if it exists
DROP TRIGGER IF EXISTS update_fees_on_payment;

DELIMITER $$

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
END$$

DELIMITER ;

-- Verify trigger was created
SHOW TRIGGERS LIKE 'fee_transactions';
