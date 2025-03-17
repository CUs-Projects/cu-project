from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Ensure required directories exist
    INSTANCE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    UPLOAD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    
    os.makedirs(INSTANCE_PATH, exist_ok=True)
    os.makedirs(UPLOAD_PATH, exist_ok=True)
    
    # Configure app
    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(INSTANCE_PATH, "university_portal.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = UPLOAD_PATH
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    with app.app_context():
        # Import models
        from .models.user import User
        from .models.application import Application
        from .models.document import Document
        from .models.certificate import Certificate
        from .models.ticket import Ticket, TicketMessage
        from .models.notification import Notification
        from .models.student_id import StudentID
        from .models.payment import Payment
        from .models.project import Project
        from .models.news import NewsAnnouncement
        from .models.program import Program
        from .models.course import Course
        
        # Create tables
        db.create_all()
        
    return app