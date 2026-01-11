from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from auth import role_required
from database import execute_query
from datetime import datetime, date
import re
import os
import uuid
from werkzeug.utils import secure_filename

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')

UPLOAD_FOLDER = 'static/uploads/materials'

# Configuration for different material types
UPLOAD_CONFIG = {
    'document': {
        'extensions': {'pdf', 'doc', 'docx', 'txt'},
        'max_size': 2 * 1024 * 1024,  # 2MB
        'max_files': 5
    },
    'presentation': {
        'extensions': {'ppt', 'pptx'},
        'max_size': 5 * 1024 * 1024,  # 5MB
        'max_files': 2
    },
    'external_video': {  # "Video" in UI
        'extensions': {'mp4', 'avi', 'mkv', 'mov'},
        'max_size': 5 * 1024 * 1024,  # 5MB
        'max_files': 5
    }
}

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_unique_filename(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}_{int(datetime.now().timestamp())}.{ext}"
    return unique_name

def extract_youtube_id(url):
    """Extract YouTube video ID from various URL formats"""
    # Patterns for: youtube.com/watch?v=ID, youtu.be/ID, youtube.com/embed/ID
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([^#\&\?]*).*'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

@teacher_bp.app_template_filter('youtube_thumb')
def youtube_thumb_filter(url):
    """Jinja filter to get thumbnail URL"""
    video_id = extract_youtube_id(url)
    if video_id:
        return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    return None

@teacher_bp.app_template_filter('youtube_id')
def youtube_id_filter(url):
    """Jinja filter to get video ID"""
    return extract_youtube_id(url)

@teacher_bp.route('/dashboard')
@role_required('teacher')
def dashboard():
    """Teacher dashboard"""
    teacher_id = session.get('teacher_id')
    
    # Get teacher's batches
    batches = execute_query(
        """SELECT b.*, c.course_name, COUNT(DISTINCT e.student_id) as student_count
           FROM batches b
           JOIN courses c ON b.course_id = c.course_id
           LEFT JOIN enrollments e ON b.batch_id = e.batch_id AND e.status = 'active'
           WHERE b.teacher_id = %s
           GROUP BY b.batch_id
           ORDER BY b.start_date DESC""",
        (teacher_id,),
        fetch=True
    )
    
    # Get recent attendance records
    recent_attendance = execute_query(
        """SELECT a.*, s.enrollment_no, u.full_name, c.course_name, b.batch_name
           FROM attendance a
           JOIN students s ON a.student_id = s.student_id
           JOIN users u ON s.user_id = u.user_id
           JOIN batches b ON a.batch_id = b.batch_id
           JOIN courses c ON b.course_id = c.course_id
           WHERE a.marked_by = %s
           ORDER BY a.attendance_date DESC, a.created_at DESC
           LIMIT 10""",
        (session.get('user_id'),),
        fetch=True
    )
    
    stats = {
        'total_batches': len(batches),
        'active_batches': len([b for b in batches if b['status'] == 'ongoing']),
        'total_students': sum(b['student_count'] for b in batches)
    }
    
    return render_template('teacher/dashboard.html', stats=stats, batches=batches, recent_attendance=recent_attendance)

@teacher_bp.route('/batches')
@role_required('teacher')
def batches():
    """View all assigned batches"""
    teacher_id = session.get('teacher_id')
    
    batches = execute_query(
        """SELECT b.*, c.course_name, c.course_code,
               COUNT(DISTINCT e.student_id) as enrolled_students
           FROM batches b
           JOIN courses c ON b.course_id = c.course_id
           LEFT JOIN enrollments e ON b.batch_id = e.batch_id AND e.status = 'active'
           WHERE b.teacher_id = %s
           GROUP BY b.batch_id
           ORDER BY b.start_date DESC""",
        (teacher_id,),
        fetch=True
    )
    
    return render_template('teacher/batches.html', batches=batches)

@teacher_bp.route('/batch/<int:batch_id>/students')
@role_required('teacher')
def batch_students(batch_id):
    """View students in a batch"""
    # Verify teacher has access to this batch
    batch = execute_query(
        """SELECT b.*, c.course_name FROM batches b
           JOIN courses c ON b.course_id = c.course_id
           WHERE b.batch_id = %s AND b.teacher_id = %s""",
        (batch_id, session.get('teacher_id')),
        fetch_one=True
    )
    
    if not batch:
        flash('Batch not found or access denied.', 'danger')
        return redirect(url_for('teacher.batches'))
    
    # Get enrolled students
    students = execute_query(
        """SELECT s.student_id, s.enrollment_no, u.full_name, u.email, s.contact,
               e.enrollment_date, e.status
           FROM enrollments e
           JOIN students s ON e.student_id = s.student_id
           JOIN users u ON s.user_id = u.user_id
           WHERE e.batch_id = %s
           ORDER BY u.full_name""",
        (batch_id,),
        fetch=True
    )
    
    return render_template('teacher/batch_students.html', batch=batch, students=students)

@teacher_bp.route('/attendance', methods=['GET', 'POST'])
@role_required('teacher')
def attendance():
    """Mark attendance"""
    teacher_id = session.get('teacher_id')
    
    if request.method == 'POST':
        batch_id = request.form.get('batch_id')
        attendance_date = request.form.get('attendance_date')
        student_ids = request.form.getlist('student_ids')
        
        # Validate date - cannot mark attendance for future dates
        selected_date_obj = datetime.strptime(attendance_date, '%Y-%m-%d').date()
        if selected_date_obj > date.today():
            flash('Cannot mark attendance for future dates! Please select today or a past date.', 'danger')
            return redirect(url_for('teacher.attendance', batch_id=batch_id, date=attendance_date))
        
        # Process attendance for each student
        for student_id in student_ids:
            status = request.form.get(f'status_{student_id}')
            remarks = request.form.get(f'remarks_{student_id}', '').strip()
            
            # Only save if status is selected (not unmarked)
            if status and status != 'unmarked':
                # Check if attendance already exists
                existing = execute_query(
                    """SELECT attendance_id FROM attendance
                       WHERE batch_id = %s AND student_id = %s AND attendance_date = %s""",
                    (batch_id, student_id, attendance_date),
                    fetch_one=True
                )
                
                if existing:
                    # Update existing
                    execute_query(
                        """UPDATE attendance SET status = %s, marked_by = %s, remarks = %s
                           WHERE attendance_id = %s""",
                        (status, session.get('user_id'), remarks if remarks else None, existing['attendance_id']),
                        commit=True
                    )
                else:
                    # Insert new
                    execute_query(
                        """INSERT INTO attendance (batch_id, student_id, attendance_date, status, marked_by, remarks)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (batch_id, student_id, attendance_date, status, session.get('user_id'), remarks if remarks else None),
                        commit=True
                    )
        
        flash('Attendance marked successfully!', 'success')
        return redirect(url_for('teacher.attendance', batch_id=batch_id, date=attendance_date))
    
    # Get teacher's batches for dropdown
    batches = execute_query(
        """SELECT b.batch_id, b.batch_name, c.course_name
           FROM batches b
           JOIN courses c ON b.course_id = c.course_id
           WHERE b.teacher_id = %s AND b.status IN ('upcoming', 'ongoing')
           ORDER BY b.batch_name""",
        (teacher_id,),
        fetch=True
    )
    
    # If batch selected, get students and batch details
    selected_batch = request.args.get('batch_id', type=int)
    students = []
    selected_date = request.args.get('date', date.today().isoformat())
    existing_attendance = {}
    batch_details = None
    
    if selected_batch:
        # Get batch details including start and end dates
        batch_details = execute_query(
            """SELECT batch_id, batch_name, start_date, end_date, status
               FROM batches
               WHERE batch_id = %s""",
            (selected_batch,),
            fetch_one=True
        )
        
        # Only allow marking attendance for ongoing batches
        if batch_details and batch_details['status'] == 'ongoing':
            students = execute_query(
                """SELECT s.student_id, s.enrollment_no, u.full_name,
                   sc.checkin_id, sc.checkin_time
                   FROM enrollments e
                   JOIN students s ON e.student_id = s.student_id
                   JOIN users u ON s.user_id = u.user_id
                   LEFT JOIN student_checkins sc ON sc.student_id = s.student_id
                       AND sc.batch_id = e.batch_id AND sc.checkin_date = %s
                   WHERE e.batch_id = %s AND e.status = 'active'
                   ORDER BY u.full_name""",
                (selected_date, selected_batch),
                fetch=True
            )
            
            # Get existing attendance for the date
            attendance_records = execute_query(
                """SELECT student_id, status, remarks FROM attendance
                   WHERE batch_id = %s AND attendance_date = %s""",
                (selected_batch, selected_date),
                fetch=True
            )
            
            for record in attendance_records:
                existing_attendance[record['student_id']] = {
                    'status': record['status'],
                    'remarks': record['remarks']
                }
        elif batch_details:
            # Batch exists but not ongoing - show message
            flash(f'Cannot mark attendance: Batch is {batch_details["status"]}. Only ongoing batches allow attendance marking.', 'warning')
    
    return render_template('teacher/attendance.html',
                         batches=batches,
                         students=students,
                         selected_batch=selected_batch,
                         selected_date=selected_date,
                         existing_attendance=existing_attendance,
                         batch_details=batch_details,
                         today=date.today().isoformat())

@teacher_bp.route('/attendance/reports')
@role_required('teacher')
def attendance_reports():
    """View attendance reports for assigned batches"""
    teacher_id = session.get('teacher_id')
    
    # Get filter parameters
    batch_id = request.args.get('batch_id', type=int)
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Get teacher's batches for filter
    batches = execute_query(
        """SELECT b.batch_id, b.batch_name, c.course_name
           FROM batches b
           JOIN courses c ON b.course_id = c.course_id
           WHERE b.teacher_id = %s
           ORDER BY b.batch_name""",
        (teacher_id,),
        fetch=True
    )
    
    # Build attendance summary query
    attendance_summary = []
    low_attendance_students = []
    batch_details = None
    
    if batch_id:
        # Verify teacher has access to this batch and get batch details
        batch_details = execute_query(
            """SELECT batch_id, batch_name, start_date, end_date 
               FROM batches 
               WHERE batch_id = %s AND teacher_id = %s""",
            (batch_id, teacher_id),
            fetch_one=True
        )
        
        if batch_details:
            # Get attendance summary for the batch
            query = """
                SELECT 
                    s.student_id,
                    s.enrollment_no,
                    u.full_name,
                    COUNT(a.attendance_id) as total_classes,
                    SUM(CASE WHEN a.status IN ('present', 'late') THEN 1 ELSE 0 END) as attended,
                    SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) as present_count,
                    SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) as absent_count,
                    SUM(CASE WHEN a.status = 'late' THEN 1 ELSE 0 END) as late_count,
                    SUM(CASE WHEN a.status = 'excused' THEN 1 ELSE 0 END) as excused_count,
                    ROUND(SUM(CASE WHEN a.status IN ('present', 'late') THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(a.attendance_id), 0), 2) as attendance_percentage
                FROM enrollments e
                JOIN students s ON e.student_id = s.student_id
                JOIN users u ON s.user_id = u.user_id
                LEFT JOIN attendance a ON a.student_id = s.student_id AND a.batch_id = e.batch_id
            """
            
            params = [batch_id]
            query += " WHERE e.batch_id = %s AND e.status = 'active'"
            
            if date_from and date_to:
                query += " AND a.attendance_date BETWEEN %s AND %s"
                params.extend([date_from, date_to])
            elif date_from:
                query += " AND a.attendance_date >= %s"
                params.append(date_from)
            elif date_to:
                query += " AND a.attendance_date <= %s"
                params.append(date_to)
            
            query += " GROUP BY s.student_id, s.enrollment_no, u.full_name ORDER BY u.full_name"
            
            attendance_summary = execute_query(query, tuple(params), fetch=True)
            
            # Identify low attendance students (< 60%)
            low_attendance_students = [
                student for student in attendance_summary 
                if student['attendance_percentage'] is not None and student['attendance_percentage'] < 60
            ]
    
    return render_template('teacher/attendance_reports.html',
                         batches=batches,
                         attendance_summary=attendance_summary,
                         low_attendance_students=low_attendance_students,
                         selected_batch=batch_id,
                         date_from=date_from,
                         date_to=date_to,
                         batch_details=batch_details)


@teacher_bp.route('/materials', methods=['GET', 'POST'])
@role_required('teacher')
def materials():
    """Upload and manage learning materials"""
    teacher_id = session.get('teacher_id')
    
    if request.method == 'POST':
        course_id = request.form.get('course_id')
        batch_id = request.form.get('batch_id') or None
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        material_type = request.form.get('material_type', 'document')
        upload_type = request.form.get('upload_type', 'link') # link or file
        
        # Determine file path based on upload type
        file_path = ''
        
        # Check if type supports file uploads
        if upload_type == 'file' and material_type in UPLOAD_CONFIG:
            config = UPLOAD_CONFIG[material_type]
            
            # Handle File Uploads (Multiple)
            files = request.files.getlist('material_files')
            
            # Filter out empty file objects
            valid_files = [f for f in files if f.filename]
            
            if not valid_files:
                flash('No files selected for upload.', 'danger')
                return redirect(url_for('teacher.materials'))
                
            if len(valid_files) > config['max_files']:
                flash(f'You can upload a maximum of {config["max_files"]} files for {material_type}.', 'warning')
                return redirect(url_for('teacher.materials'))

            saved_count = 0
            for file in valid_files:
                if file and allowed_file(file.filename, config['extensions']):
                    # Check file size (approximate, reading content length)
                    file.seek(0, os.SEEK_END)
                    file_length = file.tell()
                    file.seek(0)
                    
                    if file_length > config['max_size']:
                        limit_mb = int(config['max_size'] / (1024*1024))
                        flash(f'File "{file.filename}" exceeds the {limit_mb}MB limit. Skipped.', 'warning')
                        continue
                        
                    filename = secure_filename(file.filename)
                    unique_filename = get_unique_filename(filename)
                    
                    # Ensure directory exists
                    full_upload_path = os.path.join(current_app.root_path, UPLOAD_FOLDER)
                    os.makedirs(full_upload_path, exist_ok=True)
                    
                    save_path = os.path.join(full_upload_path, unique_filename)
                    file.save(save_path)
                    
                    # Store relative path in DB
                    db_file_path = f"/{UPLOAD_FOLDER}/{unique_filename}"
                    
                    # Insert record for each file
                    # Append index to title if multiple files
                    current_title = title
                    if len(valid_files) > 1:
                         current_title = f"{title} ({saved_count + 1})"

                    is_active = request.form.get('is_active') == 'on'
                    
                    execute_query(
                        """INSERT INTO learning_materials (course_id, batch_id, title, description,
                           material_type, file_path, uploaded_by, is_active, file_size)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (course_id, batch_id, current_title, description, material_type, db_file_path, session.get('user_id'), is_active, file_length),
                        commit=True
                    )
                    saved_count += 1
                else:
                    exts = ", ".join(config['extensions'])
                    flash(f'File "{file.filename}" has an invalid extension. Only {exts} allowed.', 'warning')
            
            if saved_count > 0:
                flash(f'{saved_count} file(s) uploaded successfully!', 'success')
            else:
                flash('No valid files were uploaded.', 'warning')
                
            return redirect(url_for('teacher.materials'))
            
        else:
            # Handle Link/URL (or unsupported file type defaulting to link?)
            file_path = request.form.get('file_path', '').strip()
            
            is_active = request.form.get('is_active') == 'on'
            
            execute_query(
                """INSERT INTO learning_materials (course_id, batch_id, title, description,
                   material_type, file_path, uploaded_by, is_active)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (course_id, batch_id, title, description, material_type, file_path, session.get('user_id'), is_active),
                commit=True
            )
            
            flash('Learning material added successfully!', 'success')
            return redirect(url_for('teacher.materials'))
    
    # Get courses taught by teacher
    courses = execute_query(
        """SELECT DISTINCT c.course_id, c.course_name
           FROM courses c
           JOIN batches b ON c.course_id = b.course_id
           WHERE b.teacher_id = %s""",
        (teacher_id,),
        fetch=True
    )
    
    # Get all materials uploaded by teacher
    uploaded_materials = execute_query(
        """SELECT m.*, c.course_name, b.batch_name
           FROM learning_materials m
           JOIN courses c ON m.course_id = c.course_id
           LEFT JOIN batches b ON m.batch_id = b.batch_id
           WHERE m.uploaded_by = %s
           ORDER BY m.upload_date DESC""",
        (session.get('user_id'),),
        fetch=True
    )
    
    return render_template('teacher/materials.html', courses=courses, materials=uploaded_materials)

@teacher_bp.route('/material/<int:material_id>/delete', methods=['POST'])
@role_required('teacher')
def delete_material(material_id):
    """Delete a learning material"""
    # Verify ownership
    material = execute_query(
        "SELECT material_id, file_path FROM learning_materials WHERE material_id = %s AND uploaded_by = %s",
        (material_id, session.get('user_id')),
        fetch_one=True
    )
    
    if not material:
        flash('Material not found or access denied.', 'danger')
        return redirect(url_for('teacher.materials'))
    
    # Delete physical file if it exists and is local (starts with /static/uploads)
    file_path = material['file_path']
    if file_path and file_path.startswith('/static/uploads/'):
        # Construct absolute path
        # Remove leading slash for os.path.join
        relative_path = file_path.lstrip('/')
        full_path = os.path.join(current_app.root_path, relative_path)
        
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
        except Exception as e:
            # Log error but continue with DB deletion
            print(f"Error deleting file {full_path}: {e}")

    execute_query(
        "DELETE FROM learning_materials WHERE material_id = %s",
        (material_id,),
        commit=True
    )
    
    flash('Material deleted successfully!', 'success')
    return redirect(url_for('teacher.materials'))

@teacher_bp.route('/material/<int:material_id>/edit', methods=['POST'])
@role_required('teacher')
def edit_material(material_id):
    """Edit a learning material"""
    # Verify ownership
    material = execute_query(
        "SELECT material_id, file_path FROM learning_materials WHERE material_id = %s AND uploaded_by = %s",
        (material_id, session.get('user_id')),
        fetch_one=True
    )
    
    if not material:
        flash('Material not found or access denied.', 'danger')
        return redirect(url_for('teacher.materials'))
    
    title = request.form.get('title', '').strip()
    course_id = request.form.get('course_id')
    batch_id = request.form.get('batch_id') or None
    material_type = request.form.get('material_type')
    description = request.form.get('description', '').strip()
    is_active = request.form.get('is_active') == 'on'
    
    # Handle File Replacement if provided
    upload_type = request.form.get('upload_type', 'link')
    new_file_path = material['file_path'] # Default to existing
    new_file_size = material['file_size'] # Default to existing
    
    if material_type == 'document' and upload_type == 'file':
         file = request.files.get('material_file') # Single file edit for now
         if file and file.filename and allowed_file(file.filename):
             # 1. Delete old file if it was local
             old_path = material['file_path']
             if old_path and old_path.startswith('/static/uploads/'):
                 relative_path = old_path.lstrip('/')
                 full_path = os.path.join(current_app.root_path, relative_path)
                 try:
                     if os.path.exists(full_path):
                         os.remove(full_path)
                 except Exception:
                     pass
            
             # 2. Save new file
             filename = secure_filename(file.filename)
             unique_filename = get_unique_filename(filename)
             full_upload_path = os.path.join(current_app.root_path, UPLOAD_FOLDER)
             os.makedirs(full_upload_path, exist_ok=True)
             save_path = os.path.join(full_upload_path, unique_filename)
             
             # Check size
             file.seek(0, os.SEEK_END)
             current_size = file.tell()
             
             if current_size <= MAX_CONTENT_LENGTH:
                 file.seek(0)
                 file.save(save_path)
                 new_file_path = f"/{UPLOAD_FOLDER}/{unique_filename}"
                 new_file_size = current_size
             else:
                 flash('New file exceeds 2MB limit. Kept old file.', 'warning')
    
    elif upload_type == 'link':
         # If switching to link or updating link
         new_file_path = request.form.get('file_path', '').strip()
    
    execute_query(
        """UPDATE learning_materials 
           SET title = %s, course_id = %s, batch_id = %s, 
               material_type = %s, file_path = %s, description = %s,
               is_active = %s, file_size = %s
           WHERE material_id = %s""",
        (title, course_id, batch_id, material_type, new_file_path, description, is_active, new_file_size, material_id),
        commit=True
    )
    
    flash('Material updated successfully!', 'success')
    return redirect(url_for('teacher.materials'))

@teacher_bp.route('/exams', methods=['GET', 'POST'])
@role_required('teacher')
def exams():
    """Manage exams and enter marks"""
    teacher_id = session.get('teacher_id')
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create_exam':
            batch_id = request.form.get('batch_id')
            exam_name = request.form.get('exam_name', '').strip()
            exam_type = request.form.get('exam_type', 'theory')
            exam_date = request.form.get('exam_date')
            total_marks = request.form.get('total_marks', 100)
            passing_marks = request.form.get('passing_marks', 40)
            duration_minutes = request.form.get('duration_minutes', 60)
            description = request.form.get('description', '').strip()
            
            execute_query(
                """INSERT INTO exams (batch_id, exam_name, exam_type, exam_date, total_marks,
                   passing_marks, duration_minutes, description, created_by)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (batch_id, exam_name, exam_type, exam_date, total_marks, passing_marks,
                 duration_minutes, description, session.get('user_id')),
                commit=True
            )
            
            flash('Exam created successfully!', 'success')
        
        elif action == 'enter_marks':
            exam_id = request.form.get('exam_id')
            student_ids = request.form.getlist('student_ids')
            marks_list = request.form.getlist('marks')
            
            # Get exam details for pass/fail calculation
            exam = execute_query(
                "SELECT total_marks, passing_marks FROM exams WHERE exam_id = %s",
                (exam_id,),
                fetch_one=True
            )
            
            for i, student_id in enumerate(student_ids):
                if i < len(marks_list) and marks_list[i]:
                    marks = int(marks_list[i])
                    result_status = 'pass' if marks >= exam['passing_marks'] else 'fail'
                    
                    # Calculate grade
                    percentage = (marks / exam['total_marks']) * 100
                    if percentage >= 90:
                        grade = 'A+'
                    elif percentage >= 80:
                        grade = 'A'
                    elif percentage >= 70:
                        grade = 'B+'
                    elif percentage >= 60:
                        grade = 'B'
                    elif percentage >= 50:
                        grade = 'C'
                    else:
                        grade = 'F'
                    
                    # Insert or update result
                    existing = execute_query(
                        "SELECT result_id FROM exam_results WHERE exam_id = %s AND student_id = %s",
                        (exam_id, student_id),
                        fetch_one=True
                    )
                    
                    if existing:
                        execute_query(
                            """UPDATE exam_results SET marks_obtained = %s, grade = %s,
                               result_status = %s, entered_by = %s
                               WHERE result_id = %s""",
                            (marks, grade, result_status, session.get('user_id'), existing['result_id']),
                            commit=True
                        )
                    else:
                        execute_query(
                            """INSERT INTO exam_results (exam_id, student_id, marks_obtained,
                               grade, result_status, entered_by)
                               VALUES (%s, %s, %s, %s, %s, %s)""",
                            (exam_id, student_id, marks, grade, result_status, session.get('user_id')),
                            commit=True
                        )
            
            flash('Marks entered successfully!', 'success')
        
        return redirect(url_for('teacher.exams'))
    
    # Get teacher's batches
    batches = execute_query(
        """SELECT b.batch_id, b.batch_name, c.course_name
           FROM batches b
           JOIN courses c ON b.course_id = c.course_id
           WHERE b.teacher_id = %s
           ORDER BY b.batch_name""",
        (teacher_id,),
        fetch=True
    )
    
    # Get all exams for teacher's batches
    exams_list = execute_query(
        """SELECT e.*, b.batch_name, c.course_name
           FROM exams e
           JOIN batches b ON e.batch_id = b.batch_id
           JOIN courses c ON b.course_id = c.course_id
           WHERE b.teacher_id = %s
           ORDER BY e.exam_date DESC""",
        (teacher_id,),
        fetch=True
    )
    
    return render_template('teacher/exams.html', batches=batches, exams=exams_list)

@teacher_bp.route('/exam/<int:exam_id>/enter-marks')
@role_required('teacher')
def enter_marks(exam_id):
    """Enter marks for an exam"""
    # Get exam details
    exam = execute_query(
        """SELECT e.*, b.batch_name, c.course_name
           FROM exams e
           JOIN batches b ON e.batch_id = b.batch_id
           JOIN courses c ON b.course_id = c.course_id
           WHERE e.exam_id = %s""",
        (exam_id,),
        fetch_one=True
    )
    
    if not exam:
        flash('Exam not found.', 'danger')
        return redirect(url_for('teacher.exams'))
    
    # Get students and their marks
    students = execute_query(
        """SELECT s.student_id, s.enrollment_no, u.full_name,
               er.marks_obtained, er.grade, er.result_status
           FROM enrollments e
           JOIN students s ON e.student_id = s.student_id
           JOIN users u ON s.user_id = u.user_id
           LEFT JOIN exam_results er ON er.student_id = s.student_id AND er.exam_id = %s
           WHERE e.batch_id = %s AND e.status = 'active'
           ORDER BY u.full_name""",
        (exam_id, exam['batch_id']),
        fetch=True
    )
    
    return render_template('teacher/enter_marks.html', exam=exam, students=students)
