from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from dotenv import load_dotenv

# Import models
from models import db
from models.user import User
from models.project import Project
from models.news import NewsAnnouncement
# ... import other models as needed

load_dotenv()

# Create Flask app first
app = Flask(__name__, 
    template_folder='templates',  # Explicitly set template folder
    static_folder='static'       # Explicitly set static folder
)

# Ensure required directories exist
INSTANCE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
UPLOAD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
PROJECTS_UPLOAD_FOLDER = os.path.join(UPLOAD_PATH, 'projects')

# Create necessary directories
for path in [INSTANCE_PATH, UPLOAD_PATH, PROJECTS_UPLOAD_FOLDER]:
    os.makedirs(path, exist_ok=True)

# Configure app
app.config['SECRET_KEY'] = 'your-secret-key-goes-here'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(INSTANCE_PATH, "university_portal.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_PATH

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def allowed_file(filename):
    """Check if uploaded file has an allowed extension"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_admin():
    """Initialize the admin user."""
    with app.app_context():
        admin = User.query.filter_by(email='admin@example.com').first()
        if not admin:
            admin = User(
                email='admin@example.com',
                full_name='Admin User',
                role='admin'
            )
            admin.set_password('adminpassword')
            db.session.add(admin)
            db.session.commit()
            print('Admin user created successfully')
        else:
            print('Admin user already exists')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_admin()
    app.run(debug=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.template_filter('time_ago')
def time_ago_filter(time):
    """Format a timestamp as 'time ago' (e.g., "3 hours ago")"""
    now = datetime.utcnow()
    diff = now - time
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    else:
        return time.strftime("%Y-%m-%d")
    

    
@app.template_filter('initials')
def initials_filter(name):
    if not name:
        return "UN"
    
    parts = name.split()
    if len(parts) == 1:
        return parts[0][0].upper()
    else:
        return (parts[0][0] + parts[-1][0]).upper()


@app.template_filter('slice')
def slice_filter(iterable, start, end=None):
    if end is None:
        return iterable[start:]
    return iterable[start:end]


@app.template_filter('format_date')
def format_date_filter(date):
    if date is None:
        return ""
    try:
        return date.strftime("%b %d, %Y")
    except:
        return str(date)    


@app.route('/')
def index():
    try:
        # Fetch featured projects
        featured_projects = Project.query.filter_by(is_active=True)\
            .order_by(Project.created_at.desc())\
            .limit(3)\
            .all()

        # Fetch latest news and announcements
        news_items = NewsAnnouncement.query.filter_by(type='news')\
            .order_by(NewsAnnouncement.date.desc())\
            .limit(3)\
            .all()

        announcements = NewsAnnouncement.query.filter_by(type='announcement')\
            .order_by(NewsAnnouncement.date.desc())\
            .limit(3)\
            .all()

        return render_template('index.html',
                             featured_projects=featured_projects,
                             news_items=news_items,
                             announcements=announcements)
    except Exception as e:
        print(f"Error in index route: {str(e)}")
        return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            if user.is_admin():
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirmPassword')
        full_name = request.form.get('fullName')
        phone = request.form.get('phone')
        nationality = request.form.get('nationality')
        education = request.form.get('education')
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered', 'danger')
            return render_template('register.html')
        
        # Create new user
        new_user = User(
            email=email,
            full_name=full_name,
            phone=phone,
            nationality=nationality,
            education=education
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/programs')
def programs():
    return render_template('programs.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))  


@app.route('/admin/applications')
@login_required

def admin_applications():
    applications = Application.query.all()
    return render_template('admin/applications.html', applications=applications)

@app.route('/admin/application/<int:application_id>/<action>', methods=['POST'])
@login_required
def admin_application_action(application_id, action):
    application = Application.query.get_or_404(application_id)
    
    if action == 'approve':
        application.status = 'Documents Approved'
        flash('Application documents approved successfully', 'success')
    elif action == 'reject':
        application.status = 'Documents Rejected'
        flash('Application documents rejected', 'warning')
    
    db.session.commit()
    return jsonify({'success': True})




@app.route('/admin/enrollments')
@login_required
def admin_enrollments():
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))
    
    # Get applications with paid status that need student IDs
    enrollments = db.session.query(Application).filter_by(
        status='Documents Approved', 
        payment_status='Paid'
    ).outerjoin(
        StudentID, 
        Application.id == StudentID.application_id
    ).filter(
        StudentID.id == None
    ).all()
    
    # Get applications with student IDs
    enrolled_students = db.session.query(Application, StudentID).join(
        StudentID, 
        Application.id == StudentID.application_id
    ).all()
    
    return render_template('admin/enrollments.html', 
                          enrollments=enrollments,
                          enrolled_students=enrolled_students)

@app.route('/admin/generate_student_id/<int:app_id>', methods=['POST'])
@login_required
def generate_student_id(app_id):
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Access denied'})
    
    application = Application.query.get_or_404(app_id)
    
    try:
        # Generate student ID based on nationality and program
        year = datetime.utcnow().year
        # Determine if student is local or international
        is_international = application.user.nationality != 'Egyptian'
        prefix = 'INT-' if is_international else 'LOC-'
        
        # Get program code from first letters of each word
        program_code = ''.join(word[0].upper() for word in application.program.split())
        
        # Find latest ID for this year, type and program
        latest_student = StudentID.query.filter(
            StudentID.student_id.like(f'{year}-{prefix}{program_code}%')
        ).order_by(StudentID.student_id.desc()).first()
        
        if latest_student:
            last_number = int(latest_student.student_id.split('-')[-1])
            new_number = str(last_number + 1).zfill(4)
        else:
            new_number = '0001'
        
        # Format: YYYY-TYPE-PROG-XXXX (e.g., 2025-INT-MBA-0001)
        student_id = f"{year}-{prefix}{program_code}-{new_number}"
        
        # Create new StudentID record
        new_student_id = StudentID(
            student_id=student_id,
            application_id=application.id
        )
        
        # Create notification for student with Arabic message
        notification = Notification(
            user_id=application.user_id,
            message=f'🎓 تم إنشاء رقم الطالب الخاص بك: {student_id}',
            read=False
        )
        
        # Update application status
        application.status = 'Enrolled'
        
        db.session.add(new_student_id)
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'student_id': student_id,
            'is_international': is_international,
            'message': 'Student ID generated successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin():
        flash('Access denied: Admin privileges required', 'danger')
        return redirect(url_for('student_dashboard'))
    
    # Get stats for dashboard
    applications_count = Application.query.filter_by(status='Pending Review').count()
    payment_pending_count = Application.query.filter_by(status='Documents Approved', payment_status='Pending').count()
    certificate_requests = Certificate.query.count()
    open_tickets = Ticket.query.filter_by(status='Open').count()
    
    # Get recent applications and tickets
    recent_applications = Application.query.order_by(Application.date_submitted.desc()).limit(3).all()
    recent_tickets = Ticket.query.order_by(Ticket.created_at.desc()).limit(3).all()
    
    # Get recent certificate requests
    recent_certificates = Certificate.query.order_by(Certificate.request_date.desc()).limit(3).all()
    
    return render_template('admin/dashboard.html', 
                          applications_count=applications_count,
                          payment_pending_count=payment_pending_count,
                          certificate_requests=certificate_requests,
                          open_tickets=open_tickets,
                          recent_applications=recent_applications,
                          recent_tickets=recent_tickets,
                          recent_certificates=recent_certificates)






# Keep only this route (around line 380)
@app.route('/admin/certificates/update/<int:cert_id>', methods=['POST'])
@login_required
def admin_update_certificate(cert_id):
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Access denied'})
    
    certificate = Certificate.query.get_or_404(cert_id)
    action = request.form.get('action')
    
    if action == 'process':
        # Update certificate status
        certificate.status = 'Ready for Pickup'
        
        # Add processing notes if provided
        notes = request.form.get('notes', '')
        if notes:
            certificate.processing_notes = notes
        
        # Create notification for student
        notification = Notification(
            user_id=certificate.user_id,
            message=f'🎉 شهادتك "{certificate.type}" جاهزة للاستلام!',
            read=False
        )
        
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'cert_id': certificate.cert_id,
            'message': 'Certificate marked as ready for pickup'
        })
    
    return jsonify({'success': False, 'message': 'Invalid action'})




@app.route('/admin/certificates')
@login_required
def admin_certificates():
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))
    
    # Get all certificates including pending payment ones
    certificates = Certificate.query.order_by(Certificate.request_date.desc()).all()
    
    return render_template('admin/certificates.html', certificates=certificates)


@app.route('/admin/tickets')
@login_required
def admin_tickets():
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))
    
    tickets = Ticket.query.order_by(Ticket.created_at.desc()).all()
    return render_template('admin/tickets.html', tickets=tickets)

@app.route('/admin/tickets/<int:ticket_id>')
@login_required
def admin_ticket_detail(ticket_id):
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))
        
    ticket = Ticket.query.get_or_404(ticket_id)
    return render_template('admin/ticket_detail.html', ticket=ticket)

@app.route('/admin/tickets/reply/<int:ticket_id>', methods=['POST'])
@login_required
def admin_ticket_reply(ticket_id):
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Access denied'})
    
    ticket = Ticket.query.get_or_404(ticket_id)
    message_text = request.form.get('message')
    
    if not message_text:
        return jsonify({'success': False, 'message': 'Message cannot be empty'})

    # Create a new message
    new_message = TicketMessage(
        ticket_id=ticket.id,
        sender='Admin',
        message=message_text
    )
    
    # Update ticket status to In Progress if it's Open
    if ticket.status == 'Open':
        ticket.status = 'In Progress'
    
    # Create notification for student
    notification = Notification(
        user_id=ticket.user_id,
        message=f'New reply to your ticket: {ticket.subject}'
    )
    
    db.session.add(new_message)
    db.session.add(notification)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/admin/tickets/update_status/<int:ticket_id>', methods=['POST'])
@login_required
def admin_update_ticket_status(ticket_id):
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Access denied'})
    
    ticket = Ticket.query.get_or_404(ticket_id)
    new_status = request.form.get('status')
    
    if new_status in ['Open', 'In Progress', 'Closed']:
        ticket.status = new_status
        
        # Notify student of status change
        notification = Notification(
            user_id=ticket.user_id,
            message=f'Your ticket {ticket.ticket_id} status has been updated to {new_status}.'
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Invalid status'})

@app.route('/admin/settings')
@login_required
def admin_settings():
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))
    
    # In a real app, you might load settings from a database
    settings = {
        'local_fee': 600,
        'international_fee': 1500,
        'certificate_fee': 200,
        'email_notifications': True,
        'sms_notifications': True,
        'push_notifications': False
    }
    
    return render_template('admin/settings.html', settings=settings)

# Student Routes
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    # Get student's applications, documents, certificates, and tickets
    applications = Application.query.filter_by(user_id=current_user.id).all()
    documents = Document.query.filter_by(user_id=current_user.id).all()
    certificates = Certificate.query.filter_by(user_id=current_user.id).all()
    tickets = Ticket.query.filter_by(user_id=current_user.id).all()
    
    # Get unread notifications
    notifications = Notification.query.filter_by(user_id=current_user.id, read=False).order_by(Notification.created_at.desc()).all()
    
    # Check if there are any applications with approved documents that need payment
    payment_required = any(app.status == 'Documents Approved' and app.payment_status == 'Pending' for app in applications)
    
    # Check if there are any certificates ready for pickup
    certificate_ready = any(cert.status == 'Ready for Pickup' for cert in certificates)
    
    return render_template('student/dashboard.html',
                          applications=applications,
                          documents=documents,
                          certificates=certificates,
                          tickets=tickets,
                          notifications=notifications,
                          payment_required=payment_required,
                          certificate_ready=certificate_ready)

@app.route('/student/applications')
@login_required
def student_applications():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    applications = Application.query.filter_by(user_id=current_user.id).order_by(Application.date_submitted.desc()).all()
    return render_template('student/applications.html', applications=applications)  # Add this return statement

@app.route('/student/applications/new', methods=['GET', 'POST'])
@login_required
def student_new_application():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        program_id = request.form.get('program')
        level = request.form.get('level')

        # Generate a unique application ID
        app_count = Application.query.count() + 1
        app_id = f"APP-{app_count:03d}"

        # Create new application
        new_application = Application(
            app_id=app_id,
            user_id=current_user.id,
            program_id=program_id,
            level=level,
            status='Pending Review',
            payment_status='Pending',
            date_submitted=datetime.utcnow()
        )

        try:
            db.session.add(new_application)
            db.session.commit()

            # Create notification for admin users
            admins = User.query.filter_by(role='admin').all()
            for admin in admins:
                notification = Notification(
                    user_id=admin.id,
                    message=f'New application received from {current_user.full_name}',
                    read=False
                )
                db.session.add(notification)
            db.session.commit()

            flash('Application submitted successfully!', 'success')
            return redirect(url_for('student_documents', app_id=new_application.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting application: {str(e)}', 'error')
            return redirect(url_for('student_new_application'))

    # GET request - show application form
    programs = Program.query.all()
    return render_template('student/new_application.html', programs=programs)

@app.route('/student/documents')
@login_required
def student_documents():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    documents = Document.query.filter_by(user_id=current_user.id).all()
    applications = Application.query.filter_by(user_id=current_user.id).all()
    return render_template('student/documents.html', documents=documents, applications=applications)

@app.route('/student/documents/upload', methods=['GET', 'POST'])
@login_required
def student_upload_document():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        document_type = request.form.get('document_type')
        application_id = request.form.get('application_id')
        
        if 'document' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['document']
        
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file:
            filename = secure_filename(file.filename)
            # Create a unique filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            new_filename = f"{current_user.id}_{timestamp}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
            
            # Create document record
            new_document = Document(
                user_id=current_user.id,
                application_id=application_id if application_id else None,
                name=document_type,
                file_path=f"uploads/{new_filename}",
                status='Uploaded'
            )
            
            db.session.add(new_document)
            db.session.commit()
            
            flash('Document uploaded successfully!', 'success')
            return redirect(url_for('student_documents'))
    
    applications = Application.query.filter_by(user_id=current_user.id).all()
    return render_template('student/upload_document.html', applications=applications)

@app.route('/student/document/delete/<int:doc_id>', methods=['POST'])
@login_required
def student_delete_document(doc_id):
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    document = Document.query.get_or_404(doc_id)
    
    # Ensure this document belongs to the current user
    if document.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('student_documents'))
    
    # Get the file path to remove it from storage
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.file_path.replace('uploads/', ''))
    
    # Delete the document from the database
    db.session.delete(document)
    db.session.commit()
    
    # Try to remove the file (if it exists)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        # Log the error but continue (document is already deleted from database)
        print(f"Error removing file: {e}")
    
    flash('Document deleted successfully', 'success')
    return redirect(url_for('student_documents'))

@app.route('/student/certificates')
@login_required
def student_certificates():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    certificates = Certificate.query.filter_by(user_id=current_user.id).all()
    return render_template('student/certificates.html', certificates=certificates)

# Keep the original route
@app.route('/student/certificates/request', methods=['GET', 'POST'])
@login_required
def student_request_certificate():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        # Create new certificate request
        certificate = Certificate(
            user_id=current_user.id,
            type=request.form.get('certificate_type'),
            purpose=request.form.get('purpose'),
            copies=int(request.form.get('copies', 1)),
            status='Pending Payment',
            cert_id=f"CERT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            request_date=datetime.now()
        )
        
        db.session.add(certificate)
        db.session.commit()
        
        flash('Certificate request submitted successfully!', 'success')
        return redirect(url_for('student_certificates'))
    
    return render_template('student/request_certificate.html')
    
@app.route('/student/support')
@login_required
def student_support():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    tickets = Ticket.query.filter_by(user_id=current_user.id).order_by(Ticket.created_at.desc()).all()
    return render_template('student/support.html', tickets=tickets)

@app.route('/student/support/new', methods=['GET', 'POST'])
@login_required
def student_new_ticket():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        if not subject or not message:
            flash('Please fill out all fields', 'danger')
            return redirect(request.url)
        
        # Generate a unique ticket ID
        ticket_count = Ticket.query.count() + 1
        ticket_id = f"TKT-{ticket_count:03d}"
        
        # Create new ticket
        new_ticket = Ticket(
            ticket_id=ticket_id,
            user_id=current_user.id,
            subject=subject,
            status='Open'
        )
        
        db.session.add(new_ticket)
        db.session.commit()
        
        # Add the first message
        first_message = TicketMessage(
            ticket_id=new_ticket.id,
            sender='Student',
            message=message
        )
        
        db.session.add(first_message)
        db.session.commit()
        
        flash('Support ticket submitted successfully!', 'success')
        return redirect(url_for('student_support'))
    
    return render_template('student/new_ticket.html')
        
@app.route('/student/support/<int:ticket_id>')
@login_required
def student_ticket_detail(ticket_id):
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Ensure this ticket belongs to the current user
    if ticket.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('student_support'))
    
    return render_template('student/ticket_detail.html', ticket=ticket)
    
@app.route('/student/support/reply/<int:ticket_id>', methods=['POST'])
@login_required
def student_ticket_reply(ticket_id):
    if current_user.is_admin():
        return jsonify({'success': False, 'message': 'Access denied'})
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Ensure this ticket belongs to the current user
    if ticket.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    message_text = request.form.get('message')
    
    if not message_text:
        return jsonify({'success': False, 'message': 'Message cannot be empty'})

    # Create a new message
    new_message = TicketMessage(
        ticket_id=ticket.id,
        sender='Student',
        message=message_text
    )
    
    db.session.add(new_message)
    db.session.commit()
    
    return jsonify({'success': True})
    
@app.route('/student/payments/<int:app_id>', methods=['GET', 'POST'])
@login_required
def student_payment(app_id):
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    application = Application.query.get_or_404(app_id)
    
    # Ensure this application belongs to the current user
    if application.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('student_applications'))
    
    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        
        # Calculate fee based on nationality
        fee = 1500 if current_user.nationality == 'International' else 600
        
        # Create payment record
        new_payment = Payment(
            user_id=current_user.id,
            application_id=application.id,
            amount=fee,
            payment_method=payment_method,
            transaction_id=f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        
        # Update application payment status
        application.payment_status = 'Paid'
        
        # Create notification without type
        notification = Notification(
            user_id=current_user.id,
            message='🎉 تم تأكيد الدفع بنجاح! سيتم مراجعة طلبك قريباً.',
            read=False,
            created_at=datetime.utcnow()
        )
        
        db.session.add(new_payment)
        db.session.add(notification)
        db.session.commit()
        
        flash('Payment processed successfully!', 'success')
        return redirect(url_for('student_applications'))
    
    # Calculate fee based on nationality
    fee = 1500 if current_user.nationality == 'International' else 600
    
    return render_template('student/payment.html', application=application, fee=fee)
    
@app.route('/student/certificate/payment/<int:cert_id>', methods=['GET', 'POST'])
@login_required
def student_certificate_payment(cert_id):
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    certificate = Certificate.query.get_or_404(cert_id)
        
    # Check if this certificate belongs to the current user
    if certificate.user_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('student_certificates'))
    
    # Calculate fee based on number of copies
    fee = 200 * certificate.copies  # 200 EGP per copy
    
    if request.method == 'POST':
        # Create payment record
        payment = Payment(
            user_id=current_user.id,
            certificate_id=certificate.id,
            amount=fee,
            payment_method='Online',
            status='Completed',
            transaction_id=f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            payment_date=datetime.utcnow()
        )
        
        # Update certificate status
        certificate.status = 'Processing'
        certificate.payment_status = 'Paid'
        
        # Create notification
        notification = Notification(
            user_id=current_user.id,
            message=f'تم تأكيد دفع طلب الشهادة {certificate.type}. سيتم معالجة طلبك قريباً.',
            read=False
        )
        
        # Notify admins
        admins = User.query.filter_by(role='admin').all()
        for admin in admins:
            admin_notification = Notification(
                user_id=admin.id,
                message=f'New certificate payment received: {certificate.type} by {current_user.full_name}',
                read=False
            )
            db.session.add(admin_notification)
        
        db.session.add(payment)
        db.session.add(notification)
        db.session.commit()
        
        flash('Payment confirmed successfully!', 'success')
        return redirect(url_for('student_certificates'))
    
    return render_template('student/certificate_payment.html', certificate=certificate, fee=fee)
    
@app.route('/student/settings')
@login_required
def student_settings():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    return render_template('student/settings.html')
        
@app.route('/student/settings/update', methods=['POST'])
@login_required
def student_update_settings():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    full_name = request.form.get('full_name')
    phone = request.form.get('phone')
    
    current_user.full_name = full_name
    current_user.phone = phone
    db.session.commit()
    
    flash('Settings updated successfully!', 'success')
    return redirect(url_for('student_settings'))

@app.route('/student/change_password', methods=['POST'])
@login_required
def student_change_password():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not current_user.check_password(current_password):
        flash('Current password is incorrect', 'danger')
        return redirect(url_for('student_settings'))
    
    if new_password != confirm_password:
        flash('New passwords do not match', 'danger')
        return redirect(url_for('student_settings'))
    
    current_user.set_password(new_password)
    db.session.commit()
    
    flash('Password changed successfully!', 'success')
    return redirect(url_for('student_settings'))

@app.route('/mark_notifications_read', methods=['POST'])
@login_required
def mark_notifications_read():
    notifications = Notification.query.filter_by(user_id=current_user.id, read=False).all()
    for notification in notifications:
        notification.read = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/student/close_ticket/<int:ticket_id>', methods=['POST'])
@login_required
def student_close_ticket(ticket_id):
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Ensure this ticket belongs to the current user
    if ticket.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('student_support'))
    
    ticket.status = 'Closed'
    db.session.commit()
    
    flash('Ticket closed successfully!', 'success')
    return redirect(url_for('student_ticket_detail', ticket_id=ticket.id))

@app.route('/student/update_notification_preferences', methods=['POST'])
@login_required
def student_update_notification_preferences():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    # In a real app, you would update user preferences in the database
    flash('Notification preferences updated successfully!', 'success')
    return redirect(url_for('student_settings'))

# Add this new command function
@click.command('init-db')
@with_appcontext
def init_db_command():
    """Initialize the database and create admin user."""
    db.create_all()
    
    # Check if admin user exists
    admin = User.query.filter_by(email='admin@example.com').first()
    if not admin:
        admin = User(
            email='admin@example.com',
            full_name='Admin User',
            role='admin'
        )
        admin.set_password('adminpassword')
        db.session.add(admin)
        db.session.commit()
        click.echo('Initialized the database and created admin user.')
    else:
        click.echo('Database already initialized.')

@app.route('/admin/projects')
@login_required
def admin_projects():
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))
    
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template('admin/projects.html', projects=projects)

@app.route('/admin/projects/new', methods=['GET', 'POST'])
@login_required
def admin_new_project():
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            description = request.form.get('description')
            category = request.form.get('category')
            url = request.form.get('url')
            is_popular = 'is_popular' in request.form
            is_active = 'is_active' in request.form
            
            # Handle image upload
            image_path = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '':
                    # Validate file extension
                    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
                    if '.' in file.filename and \
                       file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                        # Create unique filename
                        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                        original_filename = secure_filename(file.filename)
                        new_filename = f"project_{timestamp}_{original_filename}"
                        
                        # Save file with correct path
                        file_path = os.path.join(PROJECTS_UPLOAD_FOLDER, new_filename)
                        file.save(file_path)
                        
                        # Store relative path in database
                        image_path = f'uploads/projects/{new_filename}'
            
            new_project = Project(
                title=title,
                description=description,
                category=category,
                url=url,
                image_path=image_path,
                is_popular=is_popular,
                is_active=is_active,
                user_id=current_user.id
            )
            
            db.session.add(new_project)
            db.session.commit()
            
            flash('Project added successfully!', 'success')
            return redirect(url_for('admin_projects'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating project: {str(e)}', 'danger')
            return redirect(url_for('admin_new_project'))
    
    return render_template('admin/new_project.html')
    
@app.route('/admin/projects/edit/<int:project_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_project(project_id):
    if not current_user.is_admin():
        return redirect(url_for('student_dashboard'))
    
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        try:
            project.title = request.form.get('title')
            project.description = request.form.get('description')
            project.category = request.form.get('category')
            project.url = request.form.get('url')
            project.is_popular = 'is_popular' in request.form
            project.is_active = 'is_active' in request.form
            
            # Handle file upload if there's a new image
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '':
                    # Create unique filename
                    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                    filename = secure_filename(file.filename)
                    new_filename = f"project_{timestamp}_{filename}"
                    
                    # Delete old image if exists
                    if project.image_path:
                        old_file_path = os.path.join('static', project.image_path)
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)
                    
                    # Save new image
                    file_path = os.path.join(PROJECTS_UPLOAD_FOLDER, new_filename)
                    file.save(file_path)
                    
                    # Update database path
                    project.image_path = f'uploads/projects/{new_filename}'
            
            db.session.commit()
            flash('Project updated successfully!', 'success')
            return redirect(url_for('admin_projects'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating project: {str(e)}', 'error')
            return redirect(url_for('admin_edit_project', project_id=project_id))
    
    return render_template('admin/edit_project.html', project=project)
    
@app.route('/admin/projects/delete/<int:project_id>', methods=['POST'])
@login_required
def admin_delete_project(project_id):
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Access denied'})
    
    project = Project.query.get_or_404(project_id)
    
    # Delete image file if it exists
    if project.image_path:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 
                               project.image_path.replace('uploads/', ''))
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error removing file: {e}")
    
    db.session.delete(project)
    db.session.commit()
    return jsonify({'success': True})
    
@app.route('/admin/projects/toggle-status/<int:project_id>', methods=['POST'])
@login_required
    
@app.route('/admin/projects/toggle-status/<int:project_id>', methods=['POST'])
@login_required
def admin_toggle_project_status(project_id):
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Access denied'})
    
    project = Project.query.get_or_404(project_id)
    status_type = request.form.get('status_type')
    
    if status_type == 'active':
        project.is_active = not project.is_active
        status_message = 'active' if project.is_active else 'inactive'
    elif status_type == 'popular':
        project.is_popular = not project.is_popular
        status_message = 'popular' if project.is_popular else 'not popular'
    
    db.session.commit()
    return jsonify({'success': True, 'status': status_message})

@app.route('/projects')
def projects():
    # Get all active projects
    projects = Project.query.filter_by(is_active=True).order_by(Project.created_at.desc()).all()
    
    # Get unique categories
    categories = db.session.query(Project.category).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]
    
    return render_template('projects.html', 
                         projects=projects,
                         categories=categories)

@app.route('/admin/certificates/mark-ready/<int:cert_id>', methods=['POST'])
@login_required
def mark_certificate_ready(cert_id):
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Access denied'})
    
    certificate = Certificate.query.get_or_404(cert_id)
    
    try:
        # Update certificate status
        certificate.status = 'Ready for Pickup'
        
        # Create notification for student
        notification = Notification(
            user_id=certificate.user_id,
            message=f'🎉 شهادتك "{certificate.type}" جاهزة للاستلام!',
            read=False
        )
        
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Certificate marked as ready for pickup'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/admin/news', methods=['GET'])
@login_required
def admin_news():
    if not current_user.is_admin():
        return redirect(url_for('dashboard'))
    
    news_items = NewsAnnouncement.query.order_by(NewsAnnouncement.date.desc()).all()
    return render_template('admin/news.html', news_items=news_items)

import os
from werkzeug.utils import secure_filename

# Define upload paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'news')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/admin/news/add', methods=['GET', 'POST'])
@login_required
def admin_news_add():
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            description = request.form.get('description')
            type = request.form.get('type')
            date = datetime.strptime(request.form.get('date'), '%Y-%m-%d')
            
            # Handle image upload
            image = request.files.get('image')
            image_path = None
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                new_filename = f"news_{timestamp}_{filename}"
                
                # Save file with full path
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
                image.save(file_path)
                
                # Store relative path in database
                image_path = f'uploads/news/{new_filename}'
            
            news_item = NewsAnnouncement(
                title=title,
                description=description,
                type=type,
                date=date,
                image_path=image_path
            )
            
            db.session.add(news_item)
            db.session.commit()
            
            flash('News/Announcement added successfully!', 'success')
            return redirect(url_for('admin_news'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding news: {str(e)}', 'error')
            return redirect(url_for('admin_news_add'))
    
    return render_template('admin/news_add.html')
    
@app.route('/admin/news/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_news_edit(id):
    if not current_user.is_admin():
        return redirect(url_for('dashboard'))
    
    news_item = NewsAnnouncement.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            news_item.title = request.form.get('title')
            news_item.description = request.form.get('description')
            news_item.type = request.form.get('type')
            news_item.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d')
            
            # Handle image upload
            image = request.files.get('image')
            if image and image.filename and allowed_file(image.filename):
                # Delete old image if exists
                if news_item.image_path:
                    old_image_path = os.path.join(BASE_DIR, 'static', news_item.image_path)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                # Save new image
                filename = secure_filename(image.filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                new_filename = f"news_{timestamp}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
                image.save(file_path)
                
                # Update database path
                news_item.image_path = f'uploads/news/{new_filename}'
            
            db.session.commit()
            flash('News/Announcement updated successfully!', 'success')
            return redirect(url_for('admin_news'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating news: {str(e)}', 'error')
            return redirect(url_for('admin_news_edit', id=id))
    
    return render_template('admin/news_edit.html', news_item=news_item)
    
from flask import jsonify

@app.route('/admin/news/delete/<int:id>', methods=['DELETE'])
@login_required
def admin_news_delete(id):
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        news_item = NewsAnnouncement.query.get_or_404(id)
        
        # Delete associated image if exists
        if news_item.image_path:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(news_item.image_path))
            if os.path.exists(image_path):
                os.remove(image_path)
        
        db.session.delete(news_item)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Item deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/news')
def news():
    # Fetch all news and announcements
    news_items = NewsAnnouncement.query.filter_by(type='news')\
        .order_by(NewsAnnouncement.date.desc()).all()
    
    announcements = NewsAnnouncement.query.filter_by(type='announcement')\
        .order_by(NewsAnnouncement.date.desc()).all()
    
    return render_template('news.html', 
                         news_items=news_items, 
                         announcements=announcements)

# Register the command with Flask CLI
app.cli.add_command(init_db_command)

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@app.context_processor
def inject_notifications():
    if current_user.is_authenticated:
        notifications = Notification.query.filter_by(
            user_id=current_user.id
        ).order_by(
            Notification.created_at.desc()
        ).limit(10).all()
        unread_notifications = [n for n in notifications if not n.read]
        return {'notifications': notifications, 'unread_notifications': unread_notifications}
    return {'notifications': [], 'unread_notifications': []}

# Add these date formatting functions
def format_date_arabic(date):
    """Convert date to Arabic format"""
    arabic_months = {
        1: 'يناير',
        2: 'فبراير',
        3: 'مارس',
        4: 'أبريل',
        5: 'مايو',
        6: 'يونيو',
        7: 'يوليو',
        8: 'أغسطس',
        9: 'سبتمبر',
        10: 'أكتوبر',
        11: 'نوفمبر',
        12: 'ديسمبر',
    }
    day = date.day
    month = arabic_months[date.month]
    year = date.year
    return f"{day} {month} {year}"
    
# Add this context processor to make the function available in templates
@app.context_processor
def utility_processor():
    return dict(format_date_arabic=format_date_arabic)

@app.route('/test-image/<path:filename>')
def test_image(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        return str(e), 404

@app.route('/project/<int:project_id>')
def project_details(project_id):
    # Get the project details from database
    project = Project.query.get_or_404(project_id)
    return render_template('project_details.html', project=project)

@app.route('/student/courses')
@login_required
def student_courses():
    # Get student's active applications
    active_applications = Application.query.filter_by(
        user_id=current_user.id,
        status='approved',
        payment_status='paid'
    ).all()
    
    # Get courses based on program and level
    courses = []
    for application in active_applications:
        program_courses = Course.query.filter_by(
            program_id=application.program_id,
            level=application.level  # diploma, masters, doctorate
        ).order_by(Course.semester).all()
        courses.extend(program_courses)
        
    return render_template('student/courses.html', 
                         courses=courses,
                         applications=active_applications)

def init_admin():
    """Initialize the admin user."""
    admin = User.query.filter_by(email='admin@example.com').first()
    if not admin:
        admin = User(
            email='admin@example.com',
            full_name='Admin User',
            role='admin'
        )
        admin.set_password('adminpassword')
        db.session.add(admin)
        db.session.commit()
    else:
        print('Admin user already exists.')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_admin()
    app.run(debug=True)
