"""
Fix Teacher Login for username 'te'
This script resets the password to '12345' for the specific teacher account
"""

import bcrypt
from database import execute_query

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def main():
    print("="*60)
    print("FIXING TEACHER LOGIN - Username 'te'")
    print("="*60)
    
    username = "te"
    new_password = "12345"
    
    # Check if user exists
    print(f"\nChecking for user '{username}'...")
    user = execute_query(
        "SELECT * FROM users WHERE username = %s",
        (username,),
        fetch_one=True
    )
    
    if not user:
        print(f"\n❌ User '{username}' not found!")
        print("\nAvailable teacher accounts:")
        teachers = execute_query(
            "SELECT username, email, full_name FROM users WHERE role = 'teacher'",
            fetch=True
        )
        for t in teachers:
            print(f"  - Username: {t['username']}, Email: {t['email']}, Name: {t['full_name']}")
        return
    
    print(f"\n✅ User found!")
    print(f"   Username: {user['username']}")
    print(f"   Email: {user['email']}")
    print(f"   Full Name: {user['full_name']}")
    print(f"   Role: {user['role']}")
    print(f"   Status: {user['status']}")
    
    # Generate new password hash
    print(f"\n🔐 Generating new password hash for '{new_password}'...")
    password_hash = hash_password(new_password)
    
    print(f"   New hash (first 30 chars): {password_hash[:30]}...")
    
    # Update password
    print(f"\n💾 Updating password in database...")
    result = execute_query(
        "UPDATE users SET password_hash = %s WHERE username = %s",
        (password_hash, username),
        commit=True
    )
    
    if result is not None:
        print(f"\n✅ PASSWORD RESET SUCCESSFUL!")
        
        # Verify the new password
        print(f"\n🔍 Verifying password...")
        verified_user = execute_query(
            "SELECT password_hash FROM users WHERE username = %s",
            (username,),
            fetch_one=True
        )
        
        is_valid = bcrypt.checkpw(
            new_password.encode('utf-8'),
            verified_user['password_hash'].encode('utf-8')
        )
        
        if is_valid:
            print(f"   ✅ Verification successful!")
        else:
            print(f"   ❌ Verification failed!")
        
        print("\n" + "="*60)
        print("🎉 LOGIN CREDENTIALS - READY TO USE")
        print("="*60)
        print(f"\n⚠️  IMPORTANT: Use USERNAME, not email!")
        print(f"\nUsername: {username}")
        print(f"Password: {new_password}")
        print(f"\nEmail: {user['email']} (DON'T use this to login)")
        print(f"\nLogin URL: http://localhost:5000/login")
        print("\n" + "="*60)
        print("\n📝 STEPS:")
        print("1. Go to http://localhost:5000/login")
        print(f"2. Enter username: {username}")
        print(f"3. Enter password: {new_password}")
        print("4. Click Login")
        print("\n⚠️  DO NOT enter email address in username field!")
        print("="*60)
    else:
        print(f"\n❌ Failed to update password!")

if __name__ == "__main__":
    main()
