import mysql.connector
from config import Config

try:
    # Connect to database
    conn = mysql.connector.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME
    )
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    conn.commit()
    
    print("✓ Table student_checkins created successfully!")
    
    # Verify
    cursor.execute("SHOW TABLES LIKE 'student_checkins'")
    result = cursor.fetchone()
    if result:
        print("✓ Table verified in database")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"✗ Error: {e}")
