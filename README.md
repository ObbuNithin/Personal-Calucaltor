# Personalized Carbon Footprint Calculator

## 🌍 Project Overview

The Personalized Carbon Footprint Calculator is an innovative web application designed to help individuals and families understand, track, and reduce their carbon emissions through comprehensive analysis and intelligent insights.

## ✨ Key Features

### 1. Comprehensive Emission Tracking
- **Yearly Report**: Detailed emission analysis based on average weekly activities
- **Daily Tracking**: Precise carbon footprint measurement through daily input
- **Emission Categorization**: Reports rated as "Good", "Moderate", or "High"

### 2. Intelligent Insights
- **AI-Powered Chatbot**: Provides personalized recommendations for emission reduction
- **Interactive Reporting**: Actionable strategies for improving environmental impact

## 🛠 Technology Stack

### Frontend
- **HTML5/CSS3**: User interface structure and styling
- **Bootstrap**: Responsive design and components
- **JavaScript**: Enhanced interactivity and dynamic content

### Backend
- **Python (Flask)**: Web application framework
- **MySQL**: Robust database for user data and historical tracking

### Advanced Tools
- **Google Generative AI (Gemini API)**: Intelligent chatbot functionality
- **Werkzeug**: Secure file upload handling
- **Base64 Encoding**: Dynamic chart image embedding

## 📦 Prerequisites

- Python 3.8+
- pip (Python package manager)
- MySQL Database

## 🚀 Installation and Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd personal_carbon_footprint_calculator
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Database Configuration
- Create a MySQL database
- Update database credentials in `config.py`

### 4. Set Environment Variables
Create a `.env` file with:
```
GOOGLE_API_KEY=your_gemini_api_key
DATABASE_URL=your_mysql_connection_string
SECRET_KEY=your_secret_key
```

### 5. Initialize Database
```bash
python db_init.py
```

### 6. Run the Application
```bash
python app.py
```

## 🖥 Usage

1. Navigate to `http://127.0.0.1:5000/`
2. Create an account or log in
3. Input consumption data (daily or yearly)
4. View personalized carbon footprint reports
5. Interact with the AI chatbot for guidance
