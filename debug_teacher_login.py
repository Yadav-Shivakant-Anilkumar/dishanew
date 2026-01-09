"""
Test Teacher Login and Reset Password
This script helps debug teacher login issues and resets the password to a known value.
"""

import bcrypt
from database import execute_query

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, password_hash):
    """Verify a password against its hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False

def list_teachers():
    """List all teachers in the database"""
    print("\n" + "="*60)
    print("EXISTING TEACHERS")
    print("="*60)
    
    teachers = execute_query("""
        SELECT u.user_id, u.username, u.email, u.full_name, u.status, u.role,
               t.teacher_id, t.employee_id
        FROM users u
        LEFT JOIN teachers t ON u.user_id = t.user_id
        WHERE u.role = 'teacher'
        ORDER BY u.created_at DESC
    """, fetch=True)
    
    if not teachers:
        print("No teachers found in database!")
        return []
    
    for idx, teacher in enumerate(teachers, 1):
        print(f"\n{idx}. Username: {teacher['username']}")
        print(f"   Email: {teacher['email']}")
        print(f"   Full Name: {teacher['full_name']}")
        print(f"   Employee ID: {teacher['employee_id'] or 'N/A'}")
        print(f"   Status: {teacher['status']}")
        print(f"   User ID: {teacher['user_id']}")
    
    return teachers

def test_password(username, password):
    """Test if a password works for a user"""
    print(f"\n" + "="*60)
    print(f"TESTING PASSWORD FOR: {username}")
    print("="*60)
    
    user = execute_query(
        "SELECT * FROM users WHERE username = %s",
        (username,),
        fetch_one=True
    )
    
    if not user:
        print(f"❌ User '{username}' not found!")
        return False
    
    print(f"✅ User found: {user['full_name']}")
    print(f"   Role: {user['role']}")
    print(f"   Status: {user['status']}")
    
    # Test password
    stored_hash = user['password_hash']
    print(f"\n   Stored hash (first 30 chars): {stored_hash[:30]}...")
    print(f"   Testing password: '{password}'")
    
    is_valid = verify_password(password, stored_hash)
    
    if is_valid:
        print(f"\n✅ PASSWORD VALID! Login should work.")
    else:
        print(f"\n❌ PASSWORD INVALID! This password won't work for login.")
    
    return is_valid

def reset_password(username, new_password):
    """Reset password for a user"""
    print(f"\n" + "="*60)
    print(f"RESETTING PASSWORD FOR: {username}")
    print("="*60)
    
    # Check if user exists
    user = execute_query(
        "SELECT * FROM users WHERE username = %s",
        (username,),
        fetch_one=True
    )
    
    if not user:
        print(f"❌ User '{username}' not found!")
        return False
    
    # Generate new hash
    new_hash = hash_password(new_password)
    print(f"✅ User found: {user['full_name']}")
    print(f"   Generating new password hash...")
    print(f"   New hash (first 30 chars): {new_hash[:30]}...")
    
    # Update password
    result = execute_query(
        "UPDATE users SET password_hash = %s WHERE username = %s",
        (new_hash, username),
        commit=True
    )
    
    if result:
        print(f"\n✅ PASSWORD UPDATED SUCCESSFULLY!")
        print(f"   Username: {username}")
        print(f"   New Password: {new_password}")
        
        # Verify the new password works
        print(f"\n   Verifying new password...")
        if verify_password(new_password, new_hash):
            print(f"   ✅ Verification successful!")
        else:
            print(f"   ❌ Verification failed!")
        
        return True
    else:
        print(f"\n❌ FAILED TO UPDATE PASSWORD!")
        return False

def create_test_teacher():
    """Create a test teacher account"""
    print("\n" + "="*60)
    print("CREATING TEST TEACHER ACCOUNT")
    print("="*60)
    
    username = "teacher_test"
    email = "teacher@test.com"
    password = "12345"
    full_name = "Test Teacher"
    
    # Check if user already exists
    existing = execute_query(
        "SELECT * FROM users WHERE username = %s OR email = %s",
        (username, email),
        fetch_one=True
    )
    
    if existing:
        print(f"⚠️  User already exists: {existing['username']}")
        print(f"   Resetting password instead...")
        return reset_password(username, password)
    
    # Create user
    password_hash = hash_password(password)
    
    user_id = execute_query(
        """INSERT INTO users (username, email, password_hash, role, full_name, status)
           VALUES (%s, %s, %s, 'teacher', %s, 'active')""",
        (username, email, password_hash, full_name),
        commit=True
    )
    
    if user_id:
        print(f"✅ User created successfully!")
        print(f"   User ID: {user_id}")
        
        # Create teacher record
        import datetime
        employee_id = f"TCH{datetime.datetime.now().year}{user_id:03d}"
        
        teacher_id = execute_query(
            """INSERT INTO teachers (user_id, employee_id, qualification, specialization, 
                                    experience_years, contact, joining_date)
               VALUES (%s, %s, %s, %s, %s, %s, CURDATE())""",
            (user_id, employee_id, "B.Tech Computer Science", "Programming", 5, "1234567890"),
            commit=True
        )
        
        if teacher_id:
            print(f"✅ Teacher record created!")
            print(f"   Teacher ID: {teacher_id}")
            print(f"   Employee ID: {employee_id}")
            
            print("\n" + "="*60)
            print("TEST TEACHER LOGIN CREDENTIALS")
            print("="*60)
            print(f"Username: {username}")
            print(f"Password: {password}")
            print(f"Role: teacher")
            print("="*60)
            return True
    
    print(f"❌ Failed to create teacher account!")
    return False

def main():
    """Main function"""
    print("\n" + "="*80)
    print("TEACHER LOGIN DEBUG TOOL")
    print("="*80)
    
    # List existing teachers
    teachers = list_teachers()
    
    # Test with password "12345"
    if teachers:
        print("\n" + "="*80)
        print("TESTING PASSWORD '12345' FOR EACH TEACHER")
        print("="*80)
        
        for teacher in teachers:
            test_password(teacher['username'], "12345")
    
    # Ask user what to do
    print("\n" + "="*80)
    print("OPTIONS")
    print("="*80)
    print("1. Reset password for an existing teacher")
    print("2. Create a new test teacher with password '12345'")
    print("3. Exit")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        if not teachers:
            print("\n❌ No teachers found! Create one first.")
            return
        
        print("\nAvailable teachers:")
        for idx, teacher in enumerate(teachers, 1):
            print(f"{idx}. {teacher['username']} ({teacher['full_name']})")
        
        teacher_choice = input(f"\nSelect teacher (1-{len(teachers)}): ").strip()
        
        try:
            teacher_idx = int(teacher_choice) - 1
            if 0 <= teacher_idx < len(teachers):
                selected_teacher = teachers[teacher_idx]
                new_password = input("Enter new password (default: 12345): ").strip() or "12345"
                reset_password(selected_teacher['username'], new_password)
            else:
                print("❌ Invalid selection!")
        except ValueError:
            print("❌ Invalid input!")
    
    elif choice == "2":
        create_test_teacher()
    
    else:
        print("\nExiting...")

if __name__ == "__main__":
    main()
