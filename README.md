Hospital Management System (HMS)

This is a web-based Hospital Management System built with Flask and SQLite. The application provides a platform for Admins, Doctors, and Patients to manage hospital operations efficiently, including profiles, appointments, and treatment histories.

Features

The system is designed with three distinct user roles, each with specific functionalities.

1. Admin (Hospital Staff)

Pre-existing User: The admin (username: admin, password: admin123) is created programmatically. No registration is required.

Dashboard: View statistics (total doctors, patients, appointments).

Doctor Management: Add, update, and delete doctor profiles and their login credentials.

Patient Management: Update and delete patient profiles.

Appointment Viewing: View a complete list of all appointments in the system.

Search: Search for doctors (by name/specialization) and patients (by name/ID/contact).

2. Doctor

Dashboard: View all upcoming appointments for the day/week and a list of assigned patients.

Appointment Management: Mark appointments as "Completed" or "Cancelled".

Treatment Records: Enter diagnosis, prescriptions, and notes for completed appointments.

Patient History: View the complete treatment history for any of their patients.

Availability: Update a text-based availability schedule (e.g., "Available Mon-Fri, 9am-5pm") for patients to see.

3. Patient

Self-Registration: Patients can register for a new account.

Profile Management: Patients can update their own profile information (name, contact, DOB).

Doctor Search: Search for doctors by specialization or name and view their availability notes.

Appointment Booking: Book, reschedule (by cancelling and re-booking), or cancel their own appointments.

History: View their complete appointment history (upcoming, completed, and cancelled) and read treatment details (diagnosis, prescription) for completed visits.

Tech Stack

Backend: Flask

Database: SQLite (programmatically created)

ORM: Flask-SQLAlchemy

Authentication: Flask-Login

Frontend: Jinja2 (templating), HTML5, Bootstrap 5, Font Awesome (icons)

Setup and Installation

Follow these steps to run the project on your local machine.

1. Prerequisites

Python 3.x

pip (Python package installer)

2. Clone the Repository

(Assuming you have the files in a project directory)

3. Create a Virtual Environment

It's highly recommended to use a virtual environment to manage dependencies.

# Navigate to your project directory
cd /path/to/hospital-management-system

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate


4. Install Dependencies

Install all the required Python packages.

pip install Flask Flask-SQLAlchemy Flask-Login Werkzeug


(You can also create a requirements.txt file with these package names and run pip install -r requirements.txt)

5. Run the Application

Execute the main app.py file to start the Flask server.

python app.py


The application will start in debug mode on http://127.0.0.1:5000/.

On the first run, the hospital.db file will be created automatically.

The admin user and default departments will be created programmatically.

6. Access the Application

Open your web browser and go to http://127.0.0.1:5000/.

Admin Login:

Username: admin

Password: admin123

Patient: You can register a new patient account from the registration page.

Doctor: You must be logged in as an Admin to create a doctor account.

File Structure

.
├── app.py               # Main Flask application, routes, models
├── hospital.db          # SQLite database (auto-generated)
└── templates/
    ├── base.html            # Main layout template
    ├── login.html           # Login page
    ├── register.html        # Patient registration page
    │
    ├── admin_dashboard.html # Admin dashboard
    ├── add_doctor.html      # Admin form to add doctors
    ├── edit_doctor.html     # Admin form to edit doctors
    ├── edit_patient.html    # Admin form to edit patients
    ├── admin_search.html    # Admin search page for users
    ├── admin_appointments.html # Admin view for all appointments
    │
    ├── doctor_dashboard.html   # Doctor dashboard
    ├── doctor_availability.html # Doctor form to update availability
    ├── patient_history.html    # Doctor view of patient history (also used to manage appointments)
    │
    ├── patient_dashboard.html # Patient dashboard
    ├── view_doctors.html      # Patient search page for doctors
    ├── book_appointment.html  # Patient form to book appointments
    ├── my_history.html        # Patient view of their own history
    └── edit_profile.html      # Patient form to edit their profile
