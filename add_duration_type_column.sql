-- Add duration_type column to courses table
ALTER TABLE courses 
ADD COLUMN duration_type ENUM('months', 'days') DEFAULT 'months' AFTER duration_months;

-- Update existing courses to use 'months' as default
UPDATE courses SET duration_type = 'months' WHERE duration_type IS NULL;
