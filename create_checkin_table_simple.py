from database import execute_query

# Create student_checkins table
create_table_sql = """
CREATE TABLE IF NOT EXISTS student_checkins (
    checkin_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    batch_id INT NOT NULL,
    checkin_date DATE NOT NULL,
    checkin_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (batch_id) REFERENCES batches(batch_id) ON DELETE CASCADE,
    UNIQUE KEY unique_checkin (student_id, batch_id, checkin_date),
    INDEX idx_checkin_lookup (batch_id, checkin_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

try:
    execute_query(create_table_sql, commit=True)
    print("✓ student_checkins table created successfully!")
    
    # Verify
    result = execute_query("SHOW TABLES LIKE 'student_checkins'", fetch=True)
    if result:
        print("✓ Table verified - exists in database")
    else:
        print("✗ Table not found")
except Exception as e:
    print(f"Error: {e}")
