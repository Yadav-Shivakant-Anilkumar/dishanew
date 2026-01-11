
@student_bp.route('/checkin/<int:batch_id>', methods=['POST'])
@role_required('student')
def checkin(batch_id):
    """Student self-check-in for today's class"""
    student_id = session.get('student_id')
    today = date.today().isoformat()
    
    # Verify student is enrolled in this batch and batch is active
    enrollment = execute_query(
        """SELECT e.enrollment_id FROM enrollments e
           JOIN batches b ON e.batch_id = b.batch_id
           WHERE e.student_id = %s AND e.batch_id = %s 
           AND e.status = 'active'
           AND b.status IN ('upcoming', 'ongoing')
           AND CURDATE() BETWEEN b.start_date AND b.end_date""",
        (student_id, batch_id),
        fetch_one=True
    )
    
    if not enrollment:
        flash('You cannot check in for this batch at this time.', 'danger')
        return redirect(url_for('student.courses'))
    
    # Check if already checked in today
    existing = execute_query(
        """SELECT checkin_id FROM student_checkins
           WHERE student_id = %s AND batch_id = %s AND checkin_date = %s""",
        (student_id, batch_id, today),
        fetch_one=True
    )
    
    if existing:
        flash('You have already checked in for this batch today!', 'info')
    else:
        # Record check-in
        execute_query(
            """INSERT INTO student_checkins (student_id, batch_id, checkin_date)
               VALUES (%s, %s, %s)""",
            (student_id, batch_id, today),
            commit=True
        )
        flash('✓ Check-in successful! You are marked as present for today.', 'success')
    
    return redirect(url_for('student.courses'))
