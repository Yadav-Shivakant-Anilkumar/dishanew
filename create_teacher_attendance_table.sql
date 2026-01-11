-- Create teacher_attendance table
CREATE TABLE IF NOT EXISTS teacher_attendance (
    attendance_id INT AUTO_INCREMENT PRIMARY KEY,
    teacher_id INT NOT NULL,
    batch_id INT NOT NULL,
    attendance_date DATE NOT NULL,
    status ENUM('present', 'absent', 'late', 'on_leave') NOT NULL,
    marked_by INT,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE,
    FOREIGN KEY (batch_id) REFERENCES batches(batch_id) ON DELETE CASCADE,
    FOREIGN KEY (marked_by) REFERENCES users(user_id) ON DELETE SET NULL,
    UNIQUE KEY unique_teacher_date (teacher_id, batch_id, attendance_date),
    INDEX idx_teacher_id (teacher_id),
    INDEX idx_batch_id (batch_id),
    INDEX idx_attendance_date (attendance_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
