
import mysql.connector
from config import Config

def add_is_active_column():
    print("Checking 'learning_materials' table for 'is_active' column...")
    
    try:
        # Connect to database
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'learning_materials' 
            AND COLUMN_NAME = 'is_active'
        """, (Config.DB_NAME,))
        
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("Column 'is_active' not found. Adding it now...")
            # Add the column
            cursor.execute("""
                ALTER TABLE learning_materials 
                ADD COLUMN is_active BOOLEAN DEFAULT TRUE
            """)
            conn.commit()
            print("✅ Successfully added 'is_active' column!")
        else:
            print("✅ Column 'is_active' already exists.")
            
        # Verify and count
        cursor.execute("SELECT COUNT(*) FROM learning_materials WHERE is_active = TRUE")
        active_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM learning_materials")
        total_count = cursor.fetchone()[0]
        
        print(f"\nStatus: {active_count} active materials out of {total_count} total materials.")
        
    except mysql.connector.Error as err:
        print(f"❌ Database Error: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    add_is_active_column()
