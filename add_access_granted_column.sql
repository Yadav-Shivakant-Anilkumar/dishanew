-- Add access_granted column to enrollments table
ALTER TABLE enrollments 
ADD COLUMN access_granted BOOLEAN DEFAULT FALSE 
COMMENT 'Admin override to grant course access regardless of payment status';
