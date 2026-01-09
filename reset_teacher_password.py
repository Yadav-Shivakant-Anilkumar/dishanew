"""
Quick Teacher Password Reset - Automated
This script automatically resets the teacher password to '12345'
"""

import bcrypt
from database import execute_query

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def main():
    print("="*60)
    print("TEACHER PASSWORD RESET TOOL")
    print("="*60)
    
    # List all teachers
    print("\nFinding teachers in database...")
    teachers = execute_query("""
        SELECT u.user_id, u.username, u.email, u.full_name
        FROM users u
        WHERE u.role = 'teacher' AND u.status = 'active'
        ORDER BY u.created_at DESC
    """, fetch=True)
    
    if not teachers:
        print("\n❌ No teachers found!")
        print("\nCreating a test teacher account...")
        
        # Create test teacher
        username = "teacher1"
        email = "teacher1@disha.com"
        password = "12345"
        full_name = "Teacher One"
        
        password_hash = hash_password(password)
        
        user_id = execute_query(
            """INSERT INTO users (username, email, password_hash, role, full_name, status)
               VALUES (%s, %s, %s, 'teacher', %s, 'active')""",
            (username, email, password_hash, full_name),
            commit=True
        )
        
        if user_id:
            # Create teacher record
            import datetime
            employee_id = f"TCH{datetime.datetime.now().year}{user_id:03d}"
            
            execute_query(
                """INSERT INTO teachers (user_id, employee_id, qualification, specialization, 
                                        experience_years, contact, joining_date)
                   VALUES (%s, %s, %s, %s, %s, %s, CURDATE())""",
                (user_id, employee_id, "B.Tech", "Computer Science", 5, "9876543210"),
                commit=True
            )
            
            print(f"\n✅ Teacher created successfully!")
            print(f"\n{'='*60}")
            print("LOGIN CREDENTIALS")
            print("="*60)
            print(f"Username: {username}")
            print(f"Password: {password}")
            print(f"URL: http://localhost:5000/login")
            print("="*60)
    else:
        print(f"\n✅ Found {len(teachers)} teacher(s):")
        for idx, teacher in enumerate(teachers, 1):
            print(f"\n{idx}. {teacher['username']} - {teacher['full_name']}")
        
        print("\nResetting passwords to '12345' for all teachers...")
        
        new_password = "12345"
        password_hash = hash_password(new_password)
        
        for teacher in teachers:
            result = execute_query(
                "UPDATE users SET password_hash = %s WHERE user_id = %s",
                (password_hash, teacher['user_id']),
                commit=True
            )
            
            if result is not None:
                print(f"✅ Reset password for: {teacher['username']}")
        
        print(f"\n{'='*60}")
        print("ALL TEACHERS - LOGIN CREDENTIALS")
        print("="*60)
        for teacher in teachers:
            print(f"\nUsername: {teacher['username']}")
            print(f"Password: {new_password}")
        print(f"\nURL: http://localhost:5000/login")
        print("="*60)
    
    print("\n✅ Done! You can now login with the credentials above.")

if __name__ == "__main__":
    main()
