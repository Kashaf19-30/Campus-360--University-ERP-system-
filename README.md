
# Campus 360 (University ERP System)
Campus360 is a web-based University Enterprise Resource Planning (ERP) System designed to bring major university academic and administrative processes together into a centralized digital platform.

The system provides dedicated dashboards and functionality for different university roles, reducing manual processes, improving data organization, and making information easier to access.

Campus360 is built using a modern React + Django REST Framework + PostgreSQL architecture and provides role-based access to different areas of the university system.

## 🌐 Project Overview


Campus360 is a full-stack University ERP System designed to centralize and simplify university academic and administrative processes.

The system provides role-based dashboards, secure authentication, CRUD operations, REST APIs, and intelligent features for different university users.
## Modules
### Purpose
- Applicant  :  Application & profile management
- Admission	:  Admission & applicant processing
-  Teacher	:   Teacher & academic management
-  Student	 :  Student academic information
- Account     : 	Fees & financial records
-  Examination : Exams, marks & results
## ✨Features

### Authentication & Authorization

- Secure user authentication
- JWT-based authentication
- Role-based access control
- Protected dashboards and routes
- Login and registration functionality
- Password validation
- Change password functionality
- Profile management
- Logout functionality
- Role-Based Dashboards

### Campus360 provides separate interfaces according to the user's role:

 - 👤 Applicant
- 🏫 Admission
- 👨‍🏫 Teacher
- 🎓 Student
- 💰 Account
- 📝 Examination

Each dashboard provides functionality relevant to that particular role.

### Intelligent Features

Campus360 also includes intelligent features designed to assist university users, such as:

- AI-assisted admission support
- Intelligent search/support functionality
- Smart account audit alerts
- Data validation and error detection
- Rule-based degree recommendation
- Automated academic decision support

The intelligent components are designed to assist users while keeping university staff involved in important decisions.

### 🎯 Rule-Based Degree Recommendation

One of Campus360's intelligent features is a **rule-based degree recommendation system** that evaluates student information and academic criteria to suggest suitable degree options.

### 🔄 Recommendation Flow

Student Information  
↓  
Academic Criteria  
↓  
Eligibility Checking  
↓  
Criteria Matching  
↓  
Score Calculation  
↓  
Recommended Degree Options

***






## 🛠️ Technologies Used

| Technology | Purpose |
|------------|---------|
| **React.js** | Building the frontend user interface |
| **JavaScript** | Frontend logic and functionality |
| **HTML5** | Structuring web pages |
| **CSS3** | Styling and responsive layouts |
| **Django** | Backend web development |
| **Django REST Framework** | Building RESTful APIs |
| **Python** | Backend programming and business logic |
| **PostgreSQL** | Storing and managing application data |
| **Axios** | Connecting the React frontend with backend APIs |
| **JWT** | User authentication and authorization |
| **React Context API** | Managing application state |
| **Git & GitHub** | Version control and project hosting |
| **Vite** | Frontend development and build tool |


## 🔗 API Communication

Campus360 uses **REST APIs** to connect the React frontend with the Django backend.

The frontend uses **Axios** to send requests and receive data from the Django REST Framework API.

### 🔄 API Flow

React Frontend  
↓  
Axios Request  
↓  
Django REST API  
↓  
Django Backend  
↓  
PostgreSQL Database  
↓  
API Response  
↓  
React Frontend

***

## 🗄️ Database

Campus360 uses **PostgreSQL** as its relational database to store and manage university data.

Django's **ORM (Object-Relational Mapping)** is used to communicate between the backend and PostgreSQL database.

### 🔄 Database Flow

Django Models  
↓  
Django ORM  
↓  
PostgreSQL  
↓  
Data Retrieved / Stored  
↓  
Django Backend

***

## Installation and Setup
### 1️⃣ Clone the Repository
git clone https://github.com/Kashaf19-30/Campus-360--University-ERP-system-.git
cd Campus-360--University-ERP-system-

### Backend Setup

Navigate to the backend:

cd backend

Create a virtual environment:

python -m venv venv

Activate it on Windows:

venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

Run migrations:

python manage.py makemigrations
python manage.py migrate

Start the Django server:

python manage.py runserver

The backend will normally run at:

http://127.0.0.1:8000/

### ⚛️ Frontend Setup

Open a new terminal and navigate to the frontend:

cd Frontend

Install dependencies:

npm install

Start the development server:

npm run dev

The frontend will normally be available at:

http://localhost:5173/
### 🚀 Future Enhancements

- 📱 Develop a mobile application
- ☁️ Deploy the system on cloud infrastructure
- 🔔 Add real-time notifications
- 💳 Integrate online fee payment
- 📊 Add advanced analytics and reporting
- 🤖 Enhance AI-based assistance
- 📅 Add advanced timetable management
- 🌐 Add multi-language support

***
   


## 📁 Project Structure

```text
Campus360/
│
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   └── ...
│
├── Frontend/
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── ...
│
├── .gitignore
└── README.md




.
