SMART CAMPUS BACKEND
====================

This is a Flask + SQLite backend connected to the Smart Campus front end.

1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Run:
   pip install -r requirements.txt
4. Start:
   python app.py
5. Open:
   http://127.0.0.1:5000

Demo login:
Email: student@college.edu
Password: 123456

Features:
- Registration and secure password hashing
- Login/logout sessions
- SQLite database
- Lost/found item reporting
- Search and category filtering
- Simple smart text/category/location matching
- Claims and verification information
- My Claims page
- Basic admin dashboard route
- Statistics API

Important:
This is a student mini-project prototype. Change app.secret_key before real deployment.
The admin role is stored in the database but there is no public admin-registration page.
To make an account an admin for testing, change its role in smart_campus.db to "admin".

The existing front-end can be replaced by these Flask templates because the templates already contain the backend routes.
