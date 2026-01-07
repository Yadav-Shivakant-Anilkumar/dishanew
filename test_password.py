import bcrypt
from database import execute_query

# Test password hashing
test_password = "test123"
hashed = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

print(f"Test password: {test_password}")
print(f"Hashed: {hashed}")

# Test verification
is_valid = bcrypt.checkpw(test_password.encode('utf-8'), hashed.encode('utf-8'))
print(f"Verification successful: {is_valid}")

# Check a teacher's password from database
teacher = execute_query(
    """SELECT u.user_id, u.username, u.password_hash, t.employee_id
       FROM teachers t
       JOIN users u ON t.user_id = u.user_id
       LIMIT 1""",
    fetch_one=True
)

if teacher:
    print(f"\nTeacher found: {teacher['username']}")
    print(f"Password hash length: {len(teacher['password_hash'])}")
    print(f"Password hash: {teacher['password_hash'][:50]}...")
