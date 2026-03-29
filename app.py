import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, time
from functools import wraps
from markupsafe import Markup, escape

# --- App Initialization ---
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

# Configuration
app.config['SECRET_KEY'] = 'your_super_secret_key_change_this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'hospital.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Database & Login Manager Initialization
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# --- Jinja Filters ---
@app.template_filter('nl2br')
def nl2br(value):
    if not value:
        return ''
    return Markup('<br>\n').join(escape(value).splitlines())

# --- Jinja Context Globals ---
@app.context_processor
def inject_dates():
    return {'today_iso': date.today().isoformat(), 'utcnow': datetime.utcnow}

# --- Database Models ---

class User(UserMixin, db.Model):
    """
    User model for authentication.
    Handles all roles: Admin, Doctor, Patient.
    """
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'doctor', 'patient'
    
    # Relationships (one-to-one)
    doctor_profile = db.relationship('Doctor', back_populates='user', uselist=False)
    patient_profile = db.relationship('Patient', back_populates='user', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'

class Department(db.Model):
    """
    Model for medical specializations/departments.
    """
    __tablename__ = 'department'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    
    # Relationships (one-to-many)
    doctors = db.relationship('Doctor', back_populates='specialization')

    def __repr__(self):
        return f'<Department {self.name}>'

class Doctor(db.Model):
    """
    Model for Doctor profiles. Linked to a User.
    """
    __tablename__ = 'doctor'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    availability_notes = db.Column(db.Text)  # For "availability for next 7 days"
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    specialization_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    
    # Relationships
    user = db.relationship('User', back_populates='doctor_profile')
    specialization = db.relationship('Department', back_populates='doctors')
    appointments = db.relationship('Appointment', back_populates='doctor')

    def __repr__(self):
        return f'<Doctor Dr. {self.name}>'

class Patient(db.Model):
    """
    Model for Patient profiles. Linked to a User.
    """
    __tablename__ = 'patient'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.Date)
    contact = db.Column(db.String(20))
    
    # Foreign Key
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    
    # Relationships
    user = db.relationship('User', back_populates='patient_profile')
    appointments = db.relationship('Appointment', back_populates='patient')

    def __repr__(self):
        return f'<Patient {self.name}>'

class Appointment(db.Model):
    """
    Model for Appointments. Links a Patient and a Doctor.
    """
    __tablename__ = 'appointment'
    id = db.Column(db.Integer, primary_key=True)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Booked') # Booked, Completed, Cancelled
    
    # Foreign Keys
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    
    # Relationships
    patient = db.relationship('Patient', back_populates='appointments')
    doctor = db.relationship('Doctor', back_populates='appointments')
    treatment = db.relationship('Treatment', back_populates='appointment', uselist=False)

    def __repr__(self):
        return f'<Appointment {self.id} on {self.appointment_date}>'

class Treatment(db.Model):
    """
    Model for Treatment records. Linked to a completed Appointment.
    """
    __tablename__ = 'treatment'
    id = db.Column(db.Integer, primary_key=True)
    diagnosis = db.Column(db.Text, nullable=False)
    prescription = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    # Foreign Key
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), unique=True, nullable=False)
    
    # Relationship
    appointment = db.relationship('Appointment', back_populates='treatment')

    def __repr__(self):
        return f'<Treatment for Appointment {self.appointment_id}>'

# --- Flask-Login Configuration ---

@login_manager.user_loader
def load_user(user_id):
    """Required by Flask-Login to load the current user from session."""
    return User.query.get(int(user_id))

# --- Custom Decorators for Role-Based Access ---

def admin_required(f):
    """Decorator to restrict access to Admins only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def doctor_required(f):
    """Decorator to restrict access to Doctors only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'doctor':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def patient_required(f):
    """Decorator to restrict access to Patients only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'patient':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Authentication Routes (Login, Register, Logout) ---

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if current_user.is_authenticated:
        return redirect_by_role(current_user.role)
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect_by_role(user.role)
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handles Patient registration."""
    if current_user.is_authenticated:
        return redirect_by_role(current_user.role)
        
    if request.method == 'POST':
        # Form data
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        contact = request.form.get('contact')
        dob_str = request.form.get('dob')

        # Backend Validation
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
        
        try:
            dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format for Date of Birth. Use YYYY-MM-DD.', 'danger')
            return redirect(url_for('register'))

        # Create new User
        new_user = User(username=username, email=email, role='patient')
        new_user.set_password(password)
        
        # Create new Patient profile
        new_patient = Patient(name=name, dob=dob, contact=contact, user=new_user)
        
        db.session.add(new_user)
        db.session.add(new_patient)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    """Logs the current user out."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

def redirect_by_role(role):
    """Helper function to redirect user based on their role after login."""
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'doctor':
        return redirect(url_for('doctor_dashboard'))
    elif role == 'patient':
        return redirect(url_for('patient_dashboard'))
    else:
        return redirect(url_for('login'))

# --- Admin Routes ---

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard displaying key statistics."""
    total_doctors = Doctor.query.count()
    total_patients = Patient.query.count()
    total_appointments = Appointment.query.count()
    
    return render_template('admin_dashboard.html',
                           total_doctors=total_doctors,
                           total_patients=total_patients,
                           total_appointments=total_appointments)

@app.route('/admin/add_doctor', methods=['GET', 'POST'])
@login_required
@admin_required
def add_doctor():
    """Admin feature to add a new doctor."""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        spec_id = request.form.get('specialization_id')

        # Validation
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('add_doctor'))
        
        # Create User for the doctor
        new_user = User(username=username, email=email, role='doctor')
        new_user.set_password(password)
        
        # Create Doctor profile
        new_doctor = Doctor(name=name, specialization_id=spec_id, user=new_user)
        
        db.session.add(new_user)
        db.session.add(new_doctor)
        db.session.commit()
        
        flash(f'Doctor {name} added successfully.', 'success')
        return redirect(url_for('admin_search'))

    departments = Department.query.all()
    return render_template('add_doctor.html', departments=departments)

@app.route('/admin/edit_doctor/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_doctor(doctor_id):
    """Admin feature to edit an existing doctor's details."""
    doctor = Doctor.query.get_or_404(doctor_id)
    if request.method == 'POST':
        doctor.name = request.form.get('name')
        doctor.user.email = request.form.get('email')
        doctor.specialization_id = request.form.get('specialization_id')
        
        db.session.commit()
        flash(f'Doctor {doctor.name} updated successfully.', 'success')
        return redirect(url_for('admin_search'))

    departments = Department.query.all()
    return render_template('edit_doctor.html', doctor=doctor, departments=departments)

@app.route('/admin/delete_doctor/<int:doctor_id>', methods=['POST'])
@login_required
@admin_required
def delete_doctor(doctor_id):
    """Admin feature to delete a doctor (blacklist/remove)."""
    doctor = Doctor.query.get_or_404(doctor_id)
    user = doctor.user
    
    # Need to handle related appointments, or set them to cascade delete
    # For simplicity, we just delete
    
    db.session.delete(doctor)
    db.session.delete(user) # Also delete the user login
    db.session.commit()
    
    flash(f'Doctor {doctor.name} has been removed.', 'success')
    return redirect(url_for('admin_search'))

@app.route('/admin/edit_patient/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_patient(patient_id):
    """Admin feature to edit a patient's details."""
    patient = Patient.query.get_or_404(patient_id)
    if request.method == 'POST':
        patient.name = request.form.get('name')
        patient.user.email = request.form.get('email')
        patient.contact = request.form.get('contact')
        
        db.session.commit()
        flash(f'Patient {patient.name} updated successfully.', 'success')
        return redirect(url_for('admin_search'))

    return render_template('edit_patient.html', patient=patient)

@app.route('/admin/delete_patient/<int:patient_id>', methods=['POST'])
@login_required
@admin_required
def delete_patient(patient_id):
    """Admin feature to delete a patient (blacklist/remove)."""
    patient = Patient.query.get_or_404(patient_id)
    user = patient.user
    
    # Handle related appointments (e.g., cascade delete or anonymize)
    # For simplicity, we delete
    
    db.session.delete(patient)
    db.session.delete(user)
    db.session.commit()
    
    flash(f'Patient {patient.name} has been removed.', 'success')
    return redirect(url_for('admin_search'))

@app.route('/admin/appointments')
@login_required
@admin_required
def admin_appointments():
    """Admin view to see all appointments in the system."""
    appointments = Appointment.query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).all()
    return render_template('admin_appointments.html', appointments=appointments)

@app.route('/admin/search', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_search():
    """Admin search page for doctors and patients."""
    doctors = []
    patients = []
    
    if request.method == 'POST':
        search_query = request.form.get('search_query', '')
        search_type = request.form.get('search_type', 'doctor') # 'doctor' or 'patient'
        
        if search_type == 'doctor':
            doctors = Doctor.query.join(Department).filter(
                (Doctor.name.ilike(f'%{search_query}%')) |
                (Department.name.ilike(f'%{search_query}%'))
            ).all()
        elif search_type == 'patient':
            patients = Patient.query.filter(
                (Patient.name.ilike(f'%{search_query}%')) |
                (Patient.contact.ilike(f'%{search_query}%')) |
                (Patient.id.ilike(f'%{search_query}%'))
            ).all()
            
    else:
        # Show all by default if no search
        doctors = Doctor.query.all()
        patients = Patient.query.all()

    return render_template('admin_search.html', doctors=doctors, patients=patients)

# --- Doctor Routes ---

@app.route('/doctor/dashboard')
@login_required
@doctor_required
def doctor_dashboard():
    """Doctor dashboard showing upcoming appointments and assigned patients."""
    doctor = current_user.doctor_profile
    today = date.today()
    
    # Upcoming appointments for today/future
    upcoming_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date >= today,
        Appointment.status == 'Booked'
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    
    # Get unique list of patients
    patient_ids = db.session.query(Appointment.patient_id).filter_by(doctor_id=doctor.id).distinct()
    patients = Patient.query.filter(Patient.id.in_(p_id[0] for p_id in patient_ids)).all()

    return render_template('doctor_dashboard.html', 
                           appointments=upcoming_appointments, 
                           patients=patients,
                           doctor=doctor)

@app.route('/doctor/availability', methods=['GET', 'POST'])
@login_required
@doctor_required
def doctor_availability():
    """Doctor feature to update their availability notes for the next 7 days."""
    doctor = current_user.doctor_profile
    
    if request.method == 'POST':
        availability_notes = request.form.get('availability_notes')
        doctor.availability_notes = availability_notes
        db.session.commit()
        flash('Availability updated successfully.', 'success')
        return redirect(url_for('doctor_dashboard'))
        
    return render_template('doctor_availability.html', doctor=doctor)

@app.route('/doctor/patient_history/<int:patient_id>')
@login_required
@doctor_required
def patient_history(patient_id):
    """Doctor view to see a specific patient's full history."""
    patient = Patient.query.get_or_404(patient_id)
    
    # Ensure doctor has 'permission' (i.e., has had an appointment)
    # This check can be enhanced, but for now we allow if doctor is logged in
    
    history = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.status == 'Completed'
    ).order_by(Appointment.appointment_date.desc()).all()
    
    return render_template('patient_history.html', patient=patient, history=history)

@app.route('/doctor/manage_appointment/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
@doctor_required
def manage_appointment(appointment_id):
    """Doctor feature to complete an appointment and add treatment notes."""
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Security check: ensure this appointment belongs to this doctor
    if appointment.doctor_id != current_user.doctor_profile.id:
        flash('You are not authorized to view this appointment.', 'danger')
        return redirect(url_for('doctor_dashboard'))

    if request.method == 'POST':
        diagnosis = request.form.get('diagnosis')
        prescription = request.form.get('prescription')
        notes = request.form.get('notes')
        
        if not diagnosis:
            flash('Diagnosis is required.', 'danger')
            return render_template('manage_appointment.html', appointment=appointment)

        # Check if treatment record already exists (for editing)
        treatment = appointment.treatment
        if not treatment:
            treatment = Treatment(appointment_id=appointment.id)
            db.session.add(treatment)
            
        treatment.diagnosis = diagnosis
        treatment.prescription = prescription
        treatment.notes = notes
        
        appointment.status = 'Completed'
        
        db.session.commit()
        flash('Appointment marked as complete and treatment saved.', 'success')
        return redirect(url_for('doctor_dashboard'))

    # We need a template for this. Let's re-use 'patient_history.html'
    # by adding a form to it, or create a new template 'manage_appointment.html'
    # For this exercise, let's assume 'patient_history.html' can also
    # be used to *update* a *current* appointment.
    # A better name would be 'manage_appointment.html'
    
    # We'll render 'patient_history.html' but pass the *specific*
    # appointment to be managed.
    
    patient = appointment.patient
    history = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.status == 'Completed',
        Appointment.id != appointment.id # Exclude current
    ).order_by(Appointment.appointment_date.desc()).all()

    # This template 'patient_history.html' will need logic:
    # "if current_appointment is passed, show update form"
    return render_template('patient_history.html', 
                           patient=patient, 
                           history=history, 
                           current_appointment=appointment)

@app.route('/doctor/cancel_appointment/<int:appointment_id>', methods=['POST'])
@login_required
@doctor_required
def doctor_cancel_appointment(appointment_id):
    """Doctor can cancel an appointment."""
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Security check
    if appointment.doctor_id != current_user.doctor_profile.id:
        flash('Not authorized.', 'danger')
        return redirect(url_for('doctor_dashboard'))
        
    appointment.status = 'Cancelled'
    db.session.commit()
    flash('Appointment has been cancelled.', 'info')
    return redirect(url_for('doctor_dashboard'))

# --- Patient Routes ---

@app.route('/patient/dashboard')
@login_required
@patient_required
def patient_dashboard():
    """Patient dashboard: search doctors, view upcoming appointments."""
    departments = Department.query.all()
    patient = current_user.patient_profile
    today = date.today()

    upcoming_appointments = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.appointment_date >= today,
        Appointment.status == 'Booked'
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()

    return render_template('patient_dashboard.html', 
                           departments=departments, 
                           appointments=upcoming_appointments)

@app.route('/patient/view_doctors', methods=['GET'])
@login_required
@patient_required
def view_doctors():
    """Patient feature to search for doctors by specialization or name."""
    search_query = request.args.get('search_query', '')
    spec_id = request.args.get('specialization_id', '')

    query = Doctor.query

    if spec_id:
        query = query.filter(Doctor.specialization_id == spec_id)
    
    if search_query:
        query = query.join(Department).filter(
            (Doctor.name.ilike(f'%{search_query}%')) |
            (Department.name.ilike(f'%{search_query}%'))
        )
        
    doctors = query.all()
    departments = Department.query.all()
    
    return render_template('view_doctors.html', 
                           doctors=doctors, 
                           departments=departments,
                           search_query=search_query,
                           spec_id=spec_id)

@app.route('/patient/book_appointment/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
@patient_required
def book_appointment(doctor_id):
    """Patient feature to book an appointment with a specific doctor."""
    doctor = Doctor.query.get_or_404(doctor_id)
    
    if request.method == 'POST':
        date_str = request.form.get('date')
        time_str = request.form.get('time')
        
        try:
            appt_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            appt_time = datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            flash('Invalid date or time format.', 'danger')
            return redirect(url_for('book_appointment', doctor_id=doctor_id))

        # Backend Validation: Check for conflicts
        existing_appointment = Appointment.query.filter_by(
            doctor_id=doctor_id,
            appointment_date=appt_date,
            appointment_time=appt_time,
            status='Booked'
        ).first()
        
        if existing_appointment:
            flash('This time slot is already booked. Please choose another.', 'danger')
            return redirect(url_for('book_appointment', doctor_id=doctor_id))
            
        # Create new appointment
        new_appointment = Appointment(
            patient_id=current_user.patient_profile.id,
            doctor_id=doctor_id,
            appointment_date=appt_date,
            appointment_time=appt_time,
            status='Booked'
        )
        
        db.session.add(new_appointment)
        db.session.commit()
        
        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('patient_dashboard'))

    return render_template('book_appointment.html', doctor=doctor)

@app.route('/patient/my_history')
@login_required
@patient_required
def my_history():
    """Patient view to see all past and upcoming appointments and treatments."""
    patient = current_user.patient_profile
    
    appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(
        Appointment.appointment_date.desc(), 
        Appointment.appointment_time.desc()
    ).all()
    
    return render_template('my_history.html', appointments=appointments)

@app.route('/patient/cancel_appointment/<int:appointment_id>', methods=['POST'])
@login_required
@patient_required
def patient_cancel_appointment(appointment_id):
    """Patient feature to cancel one of their own appointments."""
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Security check: ensure this appointment belongs to this patient
    if appointment.patient_id != current_user.patient_profile.id:
        flash('You are not authorized to cancel this appointment.', 'danger')
        return redirect(url_for('my_history'))
        
    # Logic check: Can't cancel a completed appointment
    if appointment.status == 'Completed':
        flash('Cannot cancel a completed appointment.', 'warning')
        return redirect(url_for('my_history'))

    appointment.status = 'Cancelled'
    db.session.commit()
    flash('Your appointment has been cancelled.', 'success')
    return redirect(url_for('my_history'))

@app.route('/patient/profile', methods=['GET', 'POST'])
@login_required
@patient_required
def edit_profile():
    """Patient feature to edit their own profile."""
    patient = current_user.patient_profile
    
    if request.method == 'POST':
        patient.name = request.form.get('name')
        patient.contact = request.form.get('contact')
        
        dob_str = request.form.get('dob')
        try:
            patient.dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format for Date of Birth.', 'danger')
            return redirect(url_for('edit_profile'))
            
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('patient_dashboard'))

    return render_template('edit_profile.html', patient=patient)

# --- Base Template Route (for context) ---
# This route is not meant to be accessed directly.
# Other templates will 'extend' base.html
@app.route('/base')
def base():
    # This just shows the base template, not intended for real use
    return render_template('base.html')

# --- Database Creation and App Execution ---

def init_database():
    """
    Programmatically creates the database and the pre-existing Admin user.
    """
    with app.app_context():
        db.create_all()
        
        # Check if Admin user already exists
        if not User.query.filter_by(role='admin').first():
            print("Creating pre-existing Admin user...")
            admin_user = User(
                username='admin',
                email='admin@hospital.com',
                role='admin'
            )
            admin_user.set_password('admin123') # Change this in production
            db.session.add(admin_user)
            print("Admin user created with username 'admin' and password 'admin123'")

        # Check if Departments exist
        if Department.query.count() == 0:
            print("Creating default departments...")
            depts = [
                Department(name='Cardiology', description='Heart and blood vessels.'),
                Department(name='Neurology', description='Nervous system disorders.'),
                Department(name='Orthopedics', description='Bones, joints, and muscles.'),
                Department(name='Pediatrics', description='Medical care for children.'),
                Department(name='General Medicine', description='General health checkups.')
            ]
            db.session.add_all(depts)
        
        db.session.commit()
        print("Database initialized successfully.")

if __name__ == '__main__':
    # Create database and admin user on first run
    init_database()
    app.run(debug=True)