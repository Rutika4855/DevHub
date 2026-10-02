from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import requests
import os
import io
import zipfile
from dotenv import load_dotenv
from google import genai

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)


# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)

load_dotenv()

app.secret_key = "devhub-secret-key"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

DATABASE = "devhub.db"


# ============================================================
# FLASK LOGIN
# ============================================================

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# ============================================================
# USER MODEL
# ============================================================

class User(UserMixin):

    def __init__(self, user_id, username, email, password):
        self.id = user_id
        self.username = username
        self.email = email
        self.password = password


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_db():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            technology TEXT
        )
    """)

    try:

        conn.execute(
            "ALTER TABLE projects ADD COLUMN user_id INTEGER"
        )

    except sqlite3.OperationalError:

        pass

    conn.commit()
    conn.close()


# ============================================================
# LOAD USER
# ============================================================

@login_manager.user_loader
def load_user(user_id):

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    conn.close()

    if user:

        return User(
            user["id"],
            user["username"],
            user["email"],
            user["password"]
        )

    return None


# ============================================================
# REGISTER
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:

            return "Passwords do not match!"

        hashed_password = generate_password_hash(password)

        conn = get_db()

        try:

            conn.execute(
                """
                INSERT INTO users
                (username, email, password)
                VALUES (?, ?, ?)
                """,
                (
                    username,
                    email,
                    hashed_password
                )
            )

            conn.commit()

        except sqlite3.IntegrityError:

            conn.close()

            return "Username or Email already exists!"

        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            logged_in_user = User(
                user["id"],
                user["username"],
                user["email"],
                user["password"]
            )

            login_user(logged_in_user)

            return redirect(url_for("home"))

        return "Invalid username or password!"

    return render_template("login.html")


# ============================================================
# HOME / DASHBOARD
# ============================================================

@app.route("/")
@login_required
def home():

    conn = get_db()

    project_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM projects
        WHERE user_id = ?
        """,
        (current_user.id,)
    ).fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        project_count=project_count
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(url_for("login"))


# ============================================================
# CODE EDITOR
# ============================================================

@app.route("/editor")
@login_required
def editor():

    return render_template("editor.html")


# ============================================================
# API TESTER
# ============================================================

@app.route("/api-tester", methods=["GET", "POST"])
@login_required
def api_tester():

    result = None

    if request.method == "POST":

        url = request.form["url"]
        method = request.form["method"]
        body = request.form["body"]

        try:

            if method == "GET":

                response = requests.get(
                    url,
                    timeout=10
                )

            elif method == "POST":

                response = requests.post(
                    url,
                    data=body,
                    headers={
                        "Content-Type": "application/json"
                    },
                    timeout=10
                )

            elif method == "PUT":

                response = requests.put(
                    url,
                    data=body,
                    headers={
                        "Content-Type": "application/json"
                    },
                    timeout=10
                )

            elif method == "DELETE":

                response = requests.delete(
                    url,
                    timeout=10
                )

            else:

                return "Invalid HTTP method!", 400

            result = {
                "status": response.status_code,
                "response": response.text
            }

        except Exception as e:

            result = {
                "status": "Error",
                "response": str(e)
            }

    return render_template(
        "api_tester.html",
        result=result
    )


# ============================================================
# JSON FORMATTER
# ============================================================

@app.route("/json-formatter")
@login_required
def json_formatter():

    return render_template("json_formatter.html")


# ============================================================
# SQL HELPER
# ============================================================

@app.route("/sql-helper")
@login_required
def sql_helper():

    return render_template("sql_helper.html")


# ============================================================
# README GENERATOR
# ============================================================

@app.route("/readme-generator")
@login_required
def readme_generator():

    return render_template("readme_generator.html")


# ============================================================
# GIT HELPER
# ============================================================

@app.route("/git-helper")
@login_required
def git_helper():

    return render_template("git_helper.html")


# ============================================================
# PROJECT STRUCTURE GENERATOR
# ============================================================

@app.route("/project-structure")
@login_required
def project_structure():

    return render_template("project_structure.html")

# ============================================================
# PROJECT ZIP GENERATOR
# ============================================================

@app.route("/download-project-zip", methods=["POST"])
@login_required
def download_project_zip():

    project_name = request.form.get(
        "project_name",
        "MyProject"
    ).strip()

    technology = request.form.get(
        "technology",
        "flask"
    ).strip().lower()

    safe_name = "".join(
        char if char.isalnum() or char in "_-"
        else "_"
        for char in project_name
    )

    if not safe_name:
        safe_name = "MyProject"

    memory_file = io.BytesIO()

    with zipfile.ZipFile(
        memory_file,
        "w",
        zipfile.ZIP_DEFLATED
    ) as zip_file:

        if technology == "flask":

            zip_file.writestr(
                f"{safe_name}/app.py",
                """from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return "Hello from Flask!"


if __name__ == "__main__":
    app.run(debug=True)
"""
            )

            zip_file.writestr(
                f"{safe_name}/requirements.txt",
                "Flask\n"
            )

            zip_file.writestr(
                f"{safe_name}/README.md",
                f"# {safe_name}\n\nFlask project generated by DevHub."
            )

            zip_file.writestr(
                f"{safe_name}/templates/index.html",
                """<!DOCTYPE html>
<html>
<head>
    <title>Flask Project</title>
</head>
<body>

    <h1>Welcome to Flask 🚀</h1>

</body>
</html>
"""
            )

            zip_file.writestr(
                f"{safe_name}/static/css/style.css",
                """body {
    font-family: Arial, sans-serif;
}
"""
            )

            zip_file.writestr(
                f"{safe_name}/static/js/script.js",
                """console.log("Flask project loaded!");
"""
            )

        else:

            return jsonify({
                "success": False,
                "message": "Currently only Flask ZIP generation is enabled."
            }), 400

    memory_file.seek(0)

    return send_file(
        memory_file,
        as_attachment=True,
        download_name=f"{safe_name}.zip",
        mimetype="application/zip"
    )
# ============================================================
# DEBUGGING HELPER
# ============================================================

@app.route("/debugging-helper")
@login_required
def debugging_helper():

    return render_template("debugging_helper.html")


# ============================================================
# DEVELOPER NOTES
# ============================================================

@app.route("/developer-notes")
@login_required
def developer_notes():

    return render_template("developer_notes.html")


# ============================================================
# PROJECT LIST
# ============================================================

@app.route("/projects")
@login_required
def projects():

    conn = get_db()

    project_list = conn.execute(
        """
        SELECT *
        FROM projects
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (current_user.id,)
    ).fetchall()

    conn.close()

    return render_template(
        "projects.html",
        projects=project_list
    )


# ============================================================
# ADD PROJECT
# ============================================================

@app.route("/projects/add", methods=["POST"])
@login_required
def add_project():

    name = request.form["name"]
    description = request.form["description"]
    technology = request.form["technology"]

    conn = get_db()

    conn.execute(
        """
        INSERT INTO projects
        (name, description, technology, user_id)
        VALUES (?, ?, ?, ?)
        """,
        (
            name,
            description,
            technology,
            current_user.id
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("projects"))


# ============================================================
# EDIT PROJECT
# ============================================================

@app.route(
    "/projects/edit/<int:project_id>",
    methods=["GET", "POST"]
)
@login_required
def edit_project(project_id):

    conn = get_db()

    project = conn.execute(
        """
        SELECT *
        FROM projects
        WHERE id = ? AND user_id = ?
        """,
        (
            project_id,
            current_user.id
        )
    ).fetchone()

    if project is None:

        conn.close()

        return "Project not found or access denied!", 404

    if request.method == "POST":

        name = request.form["name"]
        description = request.form["description"]
        technology = request.form["technology"]

        conn.execute(
            """
            UPDATE projects
            SET
                name = ?,
                description = ?,
                technology = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                name,
                description,
                technology,
                project_id,
                current_user.id
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("projects"))

    conn.close()

    return render_template(
        "edit_project.html",
        project=project
    )


# ============================================================
# DELETE PROJECT
# ============================================================

@app.route("/projects/delete/<int:project_id>")
@login_required
def delete_project(project_id):

    conn = get_db()

    conn.execute(
        """
        DELETE FROM projects
        WHERE id = ? AND user_id = ?
        """,
        (
            project_id,
            current_user.id
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("projects"))


# ============================================================
# DATABASE VIEWER
# ============================================================

@app.route("/database")
@login_required
def database_viewer():

    conn = get_db()

    users = conn.execute(
        """
        SELECT id, username, email
        FROM users
        ORDER BY id DESC
        """
    ).fetchall()

    projects = conn.execute(
        """
        SELECT
            id,
            name,
            description,
            technology,
            user_id
        FROM projects
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "database.html",
        users=users,
        projects=projects
    )


# ============================================================
# AI CODE EXPLAINER - PAGE
# ============================================================

@app.route("/ai-explainer", methods=["GET"])
@login_required
def ai_explainer_page():

    return render_template(
        "ai_explainer.html"
    )


# ============================================================
# AI CODE EXPLAINER - AI REQUEST
# ============================================================

@app.route("/ai-explainer", methods=["POST"])
@login_required
def ai_explainer():

    code = request.form.get(
        "code",
        ""
    ).strip()

    if not code:

        return jsonify({
            "success": False,
            "message": "Please enter some code."
        })

    if client is None:

        return jsonify({
            "success": False,
            "message": "Gemini API key is not configured."
        })

    prompt = f"""
You are an AI Code Explainer.

Analyze the following code:

CODE:
{code}

Give the answer in this format:

PURPOSE:
Explain what this code does.

LINE-BY-LINE EXPLANATION:
Explain the important lines in simple language.

OUTPUT:
Explain what output the code produces, if possible.

IMPROVEMENTS:
Suggest simple improvements if needed.

Keep the explanation beginner-friendly.
"""

    models_to_try = [
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash"
    ]

    last_error = None

    for model_name in models_to_try:

        try:

            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )

            return jsonify({
                "success": True,
                "result": response.text,
                "model": model_name
            })

        except Exception as model_error:

            last_error = str(model_error)

    return jsonify({
        "success": False,
        "message": "All Gemini models are temporarily unavailable.",
        "details": last_error
    })


# ============================================================
# AI DEBUGGER
# ============================================================

@app.route("/ai-debugger", methods=["GET", "POST"])
@login_required
def ai_debugger():

    result = None

    if request.method == "POST":

        error_text = request.form.get(
            "error_text",
            ""
        ).strip()

        if not error_text:

            result = {
                "success": False,
                "message": "Please enter an error."
            }

        elif client is None:

            result = {
                "success": False,
                "message": "Gemini API key is not configured."
            }

        else:

            prompt = f"""
You are an AI Debugging Assistant.

Analyze the following programming error:

ERROR:
{error_text}

Give the answer in this exact format:

CAUSE:
Explain what caused the error.

FIX:
Explain step-by-step how to fix it.

CORRECTED CODE:
Provide corrected code if possible.

EXPLANATION:
Explain the solution in simple beginner-friendly language.

Keep the answer clear and practical.
"""

            models_to_try = [
                "gemini-3.7-flash",
                "gemini-3.6-flash",
                "gemini-3.5-flash"
            ]

            last_error = None

            for model_name in models_to_try:

                try:

                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )

                    result = {
                        "success": True,
                        "result": response.text,
                        "model": model_name
                    }

                    break

                except Exception as model_error:

                    last_error = str(model_error)

            if result is None:

                result = {
                    "success": False,
                    "message": "All Gemini models are temporarily unavailable.",
                    "details": last_error
                }

    return render_template(
        "ai_debugger.html",
        result=result
    )


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True
    )