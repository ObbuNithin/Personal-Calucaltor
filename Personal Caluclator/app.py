from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from flask_mysqldb import MySQL
import matplotlib.pyplot as plt
import io
import base64
import matplotlib
from werkzeug.security import generate_password_hash, check_password_hash  # For password hashing
import os
from werkzeug.utils import secure_filename
import time
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
import google.generativeai as genai
import PyPDF2
from PyPDF2 import PdfReader

matplotlib.use('Agg')

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'icfms_new'

# File upload configuration
UPLOAD_FOLDER = os.path.join('static', 'images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure Gemini API
genai.configure(api_key='AIzaSyBjNqmnCaStB_J1IqDz8lrNvhnYs7Keg4g')
model = genai.GenerativeModel('gemini-pro')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

mysql = MySQL(app)

# Function to calculate carbon footprint

@app.route('/')
def home():

    return render_template('login.html')
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        age = request.form['age']
        password = request.form['password']  # Note: No hashing as per your request

        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO users_calc (username, email, phone, age, password)
                VALUES (%s, %s, %s, %s, %s)
            """, (username, email, phone, age, password))
            mysql.connection.commit()
            flash('Signup successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Signup failed: {str(e)}", "danger")
        finally:
            cursor.close()
    return render_template('signup.html')



@app.route('/login', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT user_id, password FROM users_calc WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        if user and user[1] == password:
            session['user_id'] = user[0]  # Use 'user_id' instead of 'id'
            session['email'] = email
            flash('Login successful! Start exploring.', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials. Please try again.', 'danger')
    return render_template('login.html')


def calculate_carbon_footprint(data):
    try:
        water_emissions = (
            int(data.get('showers_per_week', 0)) * int(data.get('time_in_shower', 0)) * 0.5 +
            int(data.get('laundry_per_month', 0)) * 5 +
            int(data.get('flushes_per_day', 0)) * 0.2 * 30
        )

        electricity_emissions = (
            int(data.get('laptop_hours', 0)) * 0.05 * 365 +
            int(data.get('tv_hours', 0)) * 0.06 * 365 +
            int(data.get('ac_hours', 0)) * 1.5 * 365
        )

        heat_emissions = int(data.get('heater_usage', 0)) * 10 * 52

        vehicle_emissions = {
            'gasoline': 2.31,
            'diesel': 2.68,
            'electric': 0.5
        }.get(data.get('car_type', 'gasoline'), 2.31) * int(data.get('car_miles', 0)) * 52

        public_transit_emissions = (
            int(data.get('bus_miles', 0)) * 0.089 * 52 +
            int(data.get('train_miles', 0)) * 0.041 * 52
        )

        plane_emissions = int(data.get('flight_miles', 0)) * 0.25

        total = (
            water_emissions +
            electricity_emissions +
            heat_emissions +
            vehicle_emissions +
            public_transit_emissions +
            plane_emissions
        )

        return {
            'water_emissions': round(water_emissions, 2),
            'electricity_emissions': round(electricity_emissions, 2),
            'heat_emissions': round(heat_emissions, 2),
            'vehicle_emissions': round(vehicle_emissions, 2),
            'public_transit_emissions': round(public_transit_emissions, 2),
            'plane_emissions': round(plane_emissions, 2),
            'total': round(total, 2)
        }
    except ValueError:
        flash("Invalid input detected. Please enter numeric values only.", "danger")
        return redirect(url_for('calculator'))

# Generate Pie Chart
def generate_pie_chart(footprint):
    labels = [
        'Water Emissions', 'Electricity Emissions', 'Heat Emissions',
        'Vehicle Emissions', 'Public Transit Emissions', 'Plane Emissions'
    ]
    sizes = [
        footprint['water_emissions'],
        footprint['electricity_emissions'],
        footprint['heat_emissions'],
        footprint['vehicle_emissions'],
        footprint['public_transit_emissions'],
        footprint['plane_emissions']
    ]
    colors = ['#5DADE2', '#58D68D', '#F4D03F', '#EB984E', '#AF7AC5', '#85C1E9']
    plt.figure(figsize=(6, 6))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors)
    plt.title('Carbon Footprint Breakdown')

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    chart_url = base64.b64encode(img.getvalue()).decode()
    plt.close()
    return chart_url

# Routes
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

@app.route('/calculator', methods=['GET', 'POST'])
def calculator():
    if 'user_id' not in session:
        flash('Please login first', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            # Get all form inputs with proper type conversion
            car_type = request.form.get('car_type', 'Gasoline')
            car_miles = float(request.form.get('car_miles', 0))
            bus_miles = float(request.form.get('bus_miles', 0))
            train_miles = float(request.form.get('train_miles', 0))
            flight_miles = float(request.form.get('flight_miles', 0))
            
            showers_per_week = int(request.form.get('showers_per_week', 0))
            time_in_shower = int(request.form.get('time_in_shower', 0))
            loads_of_laundry = int(request.form.get('loads_of_laundry', 0))
            
            laptop_hours = int(request.form.get('laptop_hours', 0))
            tv_hours = int(request.form.get('tv_hours', 0))
            ac_hours = int(request.form.get('ac_hours', 0))
            heater_usage = int(request.form.get('heater_usage', 0))

            # Transportation Emissions Calculations
            # Car: Weekly miles to yearly, different factors based on car type
            car_factor = 0.404 if car_type == 'Gasoline' else 0.331  # kg CO2 per mile
            yearly_car_miles = car_miles * 52
            car_emissions = yearly_car_miles * car_factor

            # Bus: Weekly miles to yearly
            yearly_bus_miles = bus_miles * 52
            bus_emissions = yearly_bus_miles * 0.14  # kg CO2 per mile

            # Train: Weekly miles to yearly
            yearly_train_miles = train_miles * 52
            train_emissions = yearly_train_miles * 0.14  # kg CO2 per mile

            # Flight: Already in yearly miles
            flight_emissions = flight_miles * 0.255  # kg CO2 per mile

            # Total transportation emissions
            transportation_emissions = car_emissions + bus_emissions + train_emissions + flight_emissions

            # Water Usage Emissions Calculations
            yearly_shower_gallons = showers_per_week * time_in_shower * 2.5 * 52  # 2.5 gallons per minute
            yearly_laundry_gallons = loads_of_laundry * 30 * 52  # 30 gallons per load
            total_water_gallons = yearly_shower_gallons + yearly_laundry_gallons
            water_emissions = total_water_gallons * 0.18 / 1000  # 0.18 kg CO2 per 1000 gallons

            # Energy Usage Emissions Calculations
            yearly_laptop_hours = laptop_hours * 365
            yearly_tv_hours = tv_hours * 365
            yearly_ac_hours = ac_hours * 365
            yearly_heater_uses = heater_usage * 52

            laptop_emissions = yearly_laptop_hours * 0.065  # kg CO2 per hour
            tv_emissions = yearly_tv_hours * 0.12  # kg CO2 per hour
            ac_emissions = yearly_ac_hours * 2.0  # kg CO2 per hour
            heater_emissions = yearly_heater_uses * 3.0  # kg CO2 per use

            electricity_emissions = laptop_emissions + tv_emissions + ac_emissions + heater_emissions

            # Calculate total emissions
            total_emissions = transportation_emissions + water_emissions + electricity_emissions

            # Print debug information
            print(f"""
            Debug Information:
            Car Emissions: {car_emissions:.2f} kg CO2
            Bus Emissions: {bus_emissions:.2f} kg CO2
            Train Emissions: {train_emissions:.2f} kg CO2
            Flight Emissions: {flight_emissions:.2f} kg CO2
            Total Transportation: {transportation_emissions:.2f} kg CO2
            Water Emissions: {water_emissions:.2f} kg CO2
            Electricity Emissions: {electricity_emissions:.2f} kg CO2
            Total Emissions: {total_emissions:.2f} kg CO2
            """)

            # Store in database
            cursor = mysql.connection.cursor()
            
            # First, clear any existing entries for this user
            cursor.execute("DELETE FROM footprints WHERE user_id = %s", (session['user_id'],))
            
            # Insert new calculation
            cursor.execute("""
                INSERT INTO footprints (
                    user_id, car_type, car_miles, bus_miles, train_miles, flight_miles,
                    showers_per_week, time_in_shower, loads_of_laundry,
                    laptop_hours, tv_hours, ac_hours, heater_usage,
                    transportation_emissions, water_emissions, electricity_emissions, total
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                session['user_id'], car_type, car_miles, bus_miles, train_miles, flight_miles,
                showers_per_week, time_in_shower, loads_of_laundry,
                laptop_hours, tv_hours, ac_hours, heater_usage,
                transportation_emissions, water_emissions, electricity_emissions, total_emissions
            ))
            
            mysql.connection.commit()
            cursor.close()

            flash('Carbon footprint calculated successfully!', 'success')
            return redirect(url_for('yearly_report'))

        except Exception as e:
            print(f"Error in calculator: {str(e)}")
            flash('Error calculating carbon footprint. Please try again.', 'danger')
            return redirect(url_for('calculator'))

    return render_template('form.html')

@app.route('/result1')
def result1():
    print("In result1 route") # Debug print
    if 'user_id' not in session:
        print("No user_id in session") # Debug print
        flash('Please log in to view results.', 'danger')
        return redirect(url_for('login'))
        
    if 'carbon_footprint' not in session:
        print("No carbon_footprint in session") # Debug print
        flash('No calculation data found. Please use the calculator first.', 'warning')
        return redirect(url_for('result1'))

    carbon_footprint = session['carbon_footprint']
    chart_url = session.get('chart_url')
    print("Rendering result1.html") # Debug print

    return render_template('result1.html',
                         carbon_footprint=carbon_footprint,
                         chart_url=chart_url)

@app.route('/report')
def report():
    """Displays a report of the user's historical carbon footprint data."""
    if 'user_id' not in session:
        flash('Please log in to view your report.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT id, water_emissions, electricity_emissions, heat_emissions,
               vehicle_emissions, public_transit_emissions, plane_emissions, total, timestamp
        FROM footprints WHERE user_id=%s
        ORDER BY timestamp DESC
    """, (user_id,))
    footprints = cursor.fetchall()
    cursor.close()

    return render_template('report.html', footprints=footprints)
@app.route('/update_profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    try:
        cursor = mysql.connection.cursor()
        if request.method == 'POST':
            # Fetch data from the form
            personal_id = request.form.get('personal_id')
            address = request.form.get('address')
            phone = request.form.get('phone')
            age = request.form.get('age')

            # Update the user profile
            cursor.execute("""
                INSERT INTO user_profiles_extended (user_id, personal_id, address, phone, age)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                personal_id = VALUES(personal_id),
                address = VALUES(address),
                phone = VALUES(phone),
                age = VALUES(age)
            """, (user_id, personal_id, address, phone, age))
            mysql.connection.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))  # Redirect back to the profile page

        # Fetch current profile details
        cursor.execute("SELECT * FROM user_profiles_extended WHERE user_id = %s", (user_id,))
        profile = cursor.fetchone()
        return render_template('profile.html', profile=profile)
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    finally:
        cursor.close()

    return render_template('profile.html')



@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access the dashboard.', 'danger')
        return redirect(url_for('login'))

    return render_template('dashboard.html')

@app.route('/daily_entry', methods=['GET', 'POST'])
def daily_entry():
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            # Get form data
            showers = int(request.form.get('showers', 0))
            shower_minutes = int(request.form.get('shower_minutes', 0))
            laptop_hours = float(request.form.get('laptop_hours', 0))
            tv_hours = float(request.form.get('tv_hours', 0))
            ac_hours = float(request.form.get('ac_hours', 0))
            car_type = request.form.get('car_type')
            car_miles = float(request.form.get('car_miles', 0))
            bus_miles = float(request.form.get('bus_miles', 0))

            # Calculate emissions
            water_emissions = (showers * shower_minutes * 0.5)
            electricity_emissions = (
                laptop_hours * 0.05 +
                tv_hours * 0.06 +
                ac_hours * 1.5
            )
            
            car_emissions_factor = {
                'gasoline': 0.404,
                'diesel': 0.440,
                'electric': 0.100
            }
            vehicle_emissions = car_miles * car_emissions_factor.get(car_type, 0.404)
            transit_emissions = bus_miles * 0.14

            total_emissions = (water_emissions + electricity_emissions + 
                             vehicle_emissions + transit_emissions)

            # Store in database
            cursor = mysql.connection.cursor()
            
            insert_query = """
                INSERT INTO dailyentry (
                    user_id, entry_date, showers, shower_minutes, 
                    laptop_hours, tv_hours, ac_hours, car_type,
                    car_miles, bus_miles, water_emissions,
                    electricity_emissions, vehicle_emissions,
                    transit_emissions, total_emissions
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                session['user_id'],
                datetime.now(),
                showers,
                shower_minutes,
                laptop_hours,
                tv_hours,
                ac_hours,
                car_type,
                car_miles,
                bus_miles,
                water_emissions,
                electricity_emissions,
                vehicle_emissions,
                transit_emissions,
                total_emissions
            )
            
            cursor.execute(insert_query, values)
            mysql.connection.commit()
            cursor.close()

            flash('Daily entry saved successfully!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            flash(f'Error saving daily entry: {str(e)}', 'danger')
            return redirect(url_for('daily_entry'))

    return render_template('daily_entry.html')

def init_db():
    cursor = mysql.connection.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dailyentry (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            entry_date DATETIME NOT NULL,
            showers INT,
            shower_minutes INT,
            laptop_hours FLOAT,
            tv_hours FLOAT,
            ac_hours FLOAT,
            car_type VARCHAR(20),
            car_miles FLOAT,
            bus_miles FLOAT,
            water_emissions FLOAT,
            electricity_emissions FLOAT,
            vehicle_emissions FLOAT,
            transit_emissions FLOAT,
            total_emissions FLOAT,
            FOREIGN KEY (user_id) REFERENCES users_calc(user_id)
        )
    ''')
    mysql.connection.commit()
    cursor.close()

# Call init_db() when the app starts
with app.app_context():
    init_db()

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/view_progress')
def view_progress():
    if 'user_id' not in session:
        flash('Please log in to view your progress.', 'danger')
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    
    try:
        # Get today's stats
        cursor.execute("""
            SELECT 
                entry_date,
                water_emissions,
                electricity_emissions,
                vehicle_emissions,
                transit_emissions,
                total_emissions,
                showers,
                shower_minutes,
                laptop_hours,
                tv_hours,
                ac_hours,
                car_miles,
                bus_miles
            FROM dailyentry 
            WHERE user_id = %s 
            AND DATE(entry_date) = CURDATE()
        """, (session['user_id'],))
        
        today_stats = cursor.fetchone()

        # Get last 7 days history
        cursor.execute("""
            SELECT 
                entry_date,
                total_emissions,
                water_emissions,
                electricity_emissions,
                vehicle_emissions
            FROM dailyentry 
            WHERE user_id = %s 
            AND entry_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            ORDER BY entry_date DESC
        """, (session['user_id'],))
        
        weekly_history = cursor.fetchall()

        # Prepare data for charts
        dates = []
        total_emissions = []
        water_data = []
        electricity_data = []
        vehicle_data = []

        for entry in weekly_history:
            dates.append(entry[0].strftime('%Y-%m-%d'))
            total_emissions.append(float(entry[1]))
            water_data.append(float(entry[2]))
            electricity_data.append(float(entry[3]))
            vehicle_data.append(float(entry[4]))

        # Calculate averages
        cursor.execute("""
            SELECT 
                AVG(total_emissions) as avg_total,
                AVG(water_emissions) as avg_water,
                AVG(electricity_emissions) as avg_electricity,
                AVG(vehicle_emissions) as avg_vehicle
            FROM dailyentry 
            WHERE user_id = %s 
            AND entry_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        """, (session['user_id'],))
        
        averages = cursor.fetchone()

        # Get detailed last 5 days activity breakdown
        cursor.execute("""
            SELECT 
                entry_date,
                water_emissions,
                electricity_emissions,
                vehicle_emissions,
                total_emissions,
                showers,
                shower_minutes,
                laptop_hours,
                tv_hours,
                ac_hours,
                car_miles,
                bus_miles,
                car_type,
                CASE 
                    WHEN total_emissions > 40 THEN 'High'
                    WHEN total_emissions > 30 THEN 'Moderate'
                    ELSE 'Good'
                END as emission_level
            FROM dailyentry 
            WHERE user_id = %s 
            AND entry_date >= DATE_SUB(CURDATE(), INTERVAL 5 DAY)
            ORDER BY entry_date DESC
        """, (session['user_id'],))
        
        daily_breakdown = cursor.fetchall()

        # Calculate day-over-day changes
        daily_changes = []
        for i in range(len(daily_breakdown) - 1):
            today = daily_breakdown[i]
            yesterday = daily_breakdown[i + 1]
            change = {
                'date': today[0],
                'total_change': ((today[4] - yesterday[4]) / yesterday[4] * 100) if yesterday[4] != 0 else 0,
                'water_change': ((today[1] - yesterday[1]) / yesterday[1] * 100) if yesterday[1] != 0 else 0,
                'electricity_change': ((today[2] - yesterday[2]) / yesterday[2] * 100) if yesterday[2] != 0 else 0,
                'vehicle_change': ((today[3] - yesterday[3]) / yesterday[3] * 100) if yesterday[3] != 0 else 0
            }
            daily_changes.append(change)

        return render_template('view_progress.html',
                             today_stats=today_stats,
                             weekly_history=weekly_history,
                             dates=dates,
                             total_emissions=total_emissions,
                             water_data=water_data,
                             electricity_data=electricity_data,
                             vehicle_data=vehicle_data,
                             averages=averages,
                             daily_breakdown=daily_breakdown,
                             daily_changes=daily_changes)

    except Exception as e:
        print(f"Error in view_progress: {e}")
        flash('Error loading progress data', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        cursor.close()

@app.route('/download_progress_pdf')
def download_progress_pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    try:
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        y = 750  # Starting y position
        
        # Title
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, y, "Carbon Footprint Summary Report")
        y -= 30
        
        p.setFont("Helvetica", 10)
        p.drawString(50, y, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        y -= 30
        
        cursor = mysql.connection.cursor()

        # Today's stats
        cursor.execute("""
            SELECT total_emissions, water_emissions, electricity_emissions, vehicle_emissions 
            FROM dailyentry 
            WHERE user_id = %s AND DATE(entry_date) = CURDATE()
        """, (session['user_id'],))
        
        today = cursor.fetchone()
        
        if today:
            p.setFont("Helvetica-Bold", 12)
            p.drawString(50, y, "Today's Emissions")
            y -= 20
            p.setFont("Helvetica", 10)
            p.drawString(70, y, f"Total: {today[0]:.2f} kg CO2e")
            p.drawString(250, y, f"Water: {today[1]:.2f} kg CO2e")
            y -= 15
            p.drawString(70, y, f"Electricity: {today[2]:.2f} kg CO2e")
            p.drawString(250, y, f"Vehicle: {today[3]:.2f} kg CO2e")
            y -= 30

        # Last 5 days
        cursor.execute("""
            SELECT entry_date, total_emissions
            FROM dailyentry 
            WHERE user_id = %s 
            ORDER BY entry_date DESC 
            LIMIT 5
        """, (session['user_id'],))
        
        recent = cursor.fetchall()
        
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "Recent History")
        y -= 20
        
        p.setFont("Helvetica", 10)
        for entry in recent:
            p.drawString(70, y, f"{entry[0].strftime('%Y-%m-%d')}: {entry[1]:.2f} kg CO2e")
            y -= 15
        y -= 15

        # Monthly averages
        cursor.execute("""
            SELECT 
                ROUND(AVG(total_emissions), 2) as avg_total,
                ROUND(AVG(water_emissions), 2) as avg_water,
                ROUND(AVG(electricity_emissions), 2) as avg_electric,
                ROUND(AVG(vehicle_emissions), 2) as avg_vehicle,
                COUNT(*) as total_days,
                MIN(total_emissions) as min_emissions,
                MAX(total_emissions) as max_emissions
            FROM dailyentry 
            WHERE user_id = %s 
            AND entry_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        """, (session['user_id'],))
        
        monthly = cursor.fetchone()
        
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "30-Day Summary")
        y -= 20
        
        p.setFont("Helvetica", 10)
        p.drawString(70, y, f"Average Daily Total: {monthly[0]} kg CO2e")
        y -= 15
        p.drawString(70, y, f"Average Water: {monthly[1]} kg CO2e")
        p.drawString(250, y, f"Average Electricity: {monthly[2]} kg CO2e")
        y -= 15
        p.drawString(70, y, f"Average Vehicle: {monthly[3]} kg CO2e")
        p.drawString(250, y, f"Days Recorded: {monthly[4]}")
        y -= 15
        p.drawString(70, y, f"Best Day: {monthly[5]:.2f} kg CO2e")
        p.drawString(250, y, f"Highest Day: {monthly[6]:.2f} kg CO2e")
        
        cursor.close()
        p.save()
        buffer.seek(0)
        
        return send_file(
            buffer,
            download_name=f'carbon_summary_{datetime.now().strftime("%Y%m%d")}.pdf',
            mimetype='application/pdf',
            as_attachment=True
        )

    except Exception as e:
        print(f"Error: {e}")
        return redirect(url_for('view_progress'))

@app.route('/carbon_analysis', methods=['GET', 'POST'])
def carbon_analysis():
    if request.method == 'POST':
        if 'pdf_file' in request.files:
            file = request.files['pdf_file']
            if file and file.filename.endswith('.pdf'):
                try:
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    
                    # Read PDF content
                    pdf_reader = PdfReader(filepath)
                    text_content = ""
                    for page in pdf_reader.pages:
                        text_content += page.extract_text()

                    # Configure Gemini
                    genai.configure(api_key='AIzaSyCkNbFQJCB1q_MbOJQw1Ycd56dsL_5M51g')
                    model = genai.GenerativeModel('gemini-pro')
                    
                    # Simplified prompt for focused analysis
                    prompt = """
                    Analyze this carbon footprint report and provide a concise analysis in these sections:
                    1. Key Findings: Total emissions and biggest contributors
                    2. Areas of Impact: Top 2-3 major emission sources
                    3. Quick Recommendations: 2-3 actionable steps to reduce emissions
                    4. Progress Note: Compare with typical household emissions
                    5. Quick Tips: 2-3 immediate changes for impact

                    Keep each section brief and focused on actionable insights.
                    """
                    
                    response = model.generate_content(prompt + text_content)
                    analysis = response.text
                    
                    # Store the content for follow-up queries
                    session['report_content'] = text_content
                    
                    # Clean up
                    os.remove(filepath)
                    
                    return render_template('carbon_analysis.html', analysis=analysis)
                    
                except Exception as e:
                    flash(f'Error: {str(e)}')
        
        elif 'user_query' in request.form:
            try:
                query = request.form['user_query']
                report_content = session.get('report_content', '')
                
                model = genai.GenerativeModel('gemini-pro')
                prompt = f"""
                Based on this carbon footprint report, answer the following question:
                Question: {query}

                Keep the answer focused and practical.
                Report content: {report_content}
                """
                
                response = model.generate_content(prompt)
                return jsonify({'response': response.text})
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
    return render_template('carbon_analysis.html')

@app.route('/yearly/report')
def yearly_report():
    if 'user_id' not in session:
        flash('Please login first', 'danger')
        return redirect(url_for('login'))
    
    try:
        user_id = session['user_id']
        cursor = mysql.connection.cursor()
        current_year = datetime.now().year

        cursor.execute("""
            SELECT 
                transportation_emissions,
                water_emissions,
                electricity_emissions,
                total,
                car_miles,
                bus_miles,
                train_miles,
                flight_miles
            FROM footprints 
            WHERE user_id = %s 
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))
        
        latest_entry = cursor.fetchone()
        cursor.close()

        thresholds = {
            'water': {'good': 100, 'warning': 500},
            'electricity': {'good': 5000, 'warning': 10000},
            'transportation': {'good': 10000, 'warning': 20000},
            'total': {'good': 15000, 'warning': 30000}
        }

        def get_status(value, category):
            try:
                value = float(value or 0)
                if value <= thresholds[category]['good']:
                    return 'success'
                elif value <= thresholds[category]['warning']:
                    return 'warning'
                return 'danger'
            except:
                return 'secondary'

        if latest_entry:
            latest_values = {
                'water': float(latest_entry[1] or 0),
                'electricity': float(latest_entry[2] or 0),
                'transportation': float(latest_entry[0] or 0),
                'total': float(latest_entry[3] or 0),
                'car_miles': float(latest_entry[4] or 0),
                'bus_miles': float(latest_entry[5] or 0),
                'train_miles': float(latest_entry[6] or 0),
                'flight_miles': float(latest_entry[7] or 0)
            }

            # Basic environmental impact calculations
            trees_needed = round(latest_values['total'] / 21.8, 1)
            car_equivalent = round(latest_values['total'] / 4600 * 365, 1)

            # Detailed breakdown calculations
            transport_breakdown = {
                'car': round((latest_values['car_miles'] * 52 * 0.404), 2),
                'bus': round((latest_values['bus_miles'] * 52 * 0.14), 2),
                'train': round((latest_values['train_miles'] * 52 * 0.14), 2),
                'flight': round((latest_values['flight_miles'] * 0.255), 2)
            }

            # Environmental equivalents
            environmental_impact = {
                'trees_cut': round(latest_values['total'] / 1000, 1),
                'ice_melted': round(latest_values['total'] * 0.089, 1),  # kg of arctic ice
                'species_affected': round(latest_values['total'] / 5000, 1),
                'ocean_acidification': round(latest_values['total'] * 0.0001, 3),  # pH change equivalent
            }

            # Recommendations based on actual values
            recommendations = []
            
            if latest_values['transportation'] > thresholds['transportation']['good']:
                recommendations.append({
                    'category': 'Transportation',
                    'icon': 'fa-car',
                    'message': 'Your transportation emissions are high.',
                    'tips': [
                        'Consider carpooling or public transport',
                        'Combine multiple errands into one trip',
                        'Regular vehicle maintenance improves efficiency',
                        'Consider an electric or hybrid vehicle'
                    ]
                })

            if latest_values['electricity'] > thresholds['electricity']['good']:
                recommendations.append({
                    'category': 'Electricity',
                    'icon': 'fa-bolt',
                    'message': 'Your electricity usage can be reduced.',
                    'tips': [
                        'Switch to LED bulbs',
                        'Use natural light when possible',
                        'Install a smart thermostat',
                        'Upgrade to energy-efficient appliances'
                    ]
                })

            if latest_values['water'] > thresholds['water']['good']:
                recommendations.append({
                    'category': 'Water',
                    'icon': 'fa-tint',
                    'message': 'Your water consumption is above average.',
                    'tips': [
                        'Take shorter showers',
                        'Fix any leaking faucets',
                        'Install water-efficient fixtures',
                        'Collect rainwater for plants'
                    ]
                })

            yearly_data = {
                'has_data': True,
                'totals': {
                    'year': current_year,
                    'water_emissions': latest_values['water'],
                    'electricity_emissions': latest_values['electricity'],
                    'transportation_emissions': latest_values['transportation'],
                    'total': latest_values['total']
                },
                'status': {
                    'water': get_status(latest_values['water'], 'water'),
                    'electricity': get_status(latest_values['electricity'], 'electricity'),
                    'transportation': get_status(latest_values['transportation'], 'transportation'),
                    'total': get_status(latest_values['total'], 'total')
                },
                'impact': {
                    'trees_needed': trees_needed,
                    'car_equivalent_days': car_equivalent,
                    'environmental': environmental_impact
                },
                'breakdown': {
                    'transport': transport_breakdown,
                    'percentage': {
                        'transport': round((latest_values['transportation'] / latest_values['total']) * 100 if latest_values['total'] > 0 else 0, 1),
                        'water': round((latest_values['water'] / latest_values['total']) * 100 if latest_values['total'] > 0 else 0, 1),
                        'electricity': round((latest_values['electricity'] / latest_values['total']) * 100 if latest_values['total'] > 0 else 0, 1)
                    }
                },
                'recommendations': recommendations
            }
        else:
            yearly_data = {
                'has_data': False,
                'totals': {
                    'year': current_year,
                    'water_emissions': 0,
                    'electricity_emissions': 0,
                    'transportation_emissions': 0,
                    'total': 0
                },
                'status': {
                    'water': 'secondary',
                    'electricity': 'secondary',
                    'transportation': 'secondary',
                    'total': 'secondary'
                },
                'impact': {
                    'trees_needed': 0,
                    'car_equivalent_days': 0,
                    'environmental': {
                        'trees_cut': 0,
                        'ice_melted': 0,
                        'species_affected': 0,
                        'ocean_acidification': 0
                    }
                },
                'breakdown': {
                    'transport': {'car': 0, 'bus': 0, 'train': 0, 'flight': 0},
                    'percentage': {'transport': 0, 'water': 0, 'electricity': 0}
                },
                'recommendations': []
            }
        
        return render_template('yearly_report.html', data=yearly_data)
        
    except Exception as e:
        print(f"Error in yearly report: {str(e)}")
        return redirect(url_for('calculator'))

@app.route('/test_data')
def test_data():
    if 'user_id' not in session:
        return "Please login first"
    
    cursor = mysql.connection.cursor()
    
    # Get the latest entry with all details
    cursor.execute("""
        SELECT 
            car_type, car_miles, bus_miles, train_miles, flight_miles,
            transportation_emissions, water_emissions, electricity_emissions, total,
            created_at
        FROM footprints 
        WHERE user_id = %s 
        ORDER BY created_at DESC 
        LIMIT 1
    """, (session['user_id'],))
    
    data = cursor.fetchone()
    cursor.close()
    
    if data:
        return f"""
            <h3>Latest Entry:</h3>
            <p>Car Type: {data[0]}</p>
            <p>Car Miles: {data[1]}</p>
            <p>Bus Miles: {data[2]}</p>
            <p>Train Miles: {data[3]}</p>
            <p>Flight Miles: {data[4]}</p>
            <p>Transportation Emissions: {data[5]}</p>
            <p>Water Emissions: {data[6]}</p>
            <p>Electricity Emissions: {data[7]}</p>
            <p>Total: {data[8]}</p>
            <p>Created At: {data[9]}</p>
        """
    return "No data found"

if __name__ == '__main__':
    app.run(debug=True,port=5001)
    