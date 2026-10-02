from flask import Flask, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import requests
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)

app = Flask(__name__)

DATABASE = "devhub.db"

app = Flask(__name__)

app.secret_key = "devhub-secret-key"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

DATABASE = "devhub.db"
class User(UserMixin):

    def __init__(self, user_id, username, email, password):
        self.id = user_id
        self.username = username
        self.email = email
        self.password = password


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
def get_db():

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


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
                INSERT INTO users (username, email, password)
                VALUES (?, ?, ?)
                """,
                (username, email, hashed_password)
            )

            conn.commit()

        except sqlite3.IntegrityError:

            conn.close()

            return "Username or Email already exists!"

        conn.close()

        return "Registration successful!"

    return render_template("register.html")
@app.route("/login", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

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
@app.route("/")
@login_required
def home():
    return render_template("index.html")
@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(url_for("login"))
@app.route("/editor")
def editor():
    return render_template("editor.html")

@app.route("/api-tester", methods=["GET", "POST"])
def api_tester():

    result = None

    if request.method == "POST":

        url = request.form["url"]
        method = request.form["method"]
        body = request.form["body"]

        try:

            if method == "GET":
                response = requests.get(url, timeout=10)

            elif method == "POST":
                response = requests.post(
                    url,
                    data=body,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )

            elif method == "PUT":
                response = requests.put(
                    url,
                    data=body,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )

            elif method == "DELETE":
                response = requests.delete(
                    url,
                    timeout=10
                )

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
@app.route("/json-formatter")
def json_formatter():
    return render_template("json_formatter.html")
@app.route("/sql-helper")
def sql_helper():
    return render_template("sql_helper.html")
@app.route("/readme-generator")
def readme_generator():
    return render_template("readme_generator.html")
@app.route("/projects")
@login_required
def projects():

    conn = get_db()

    project_list = conn.execute(
        """
        SELECT * FROM projects
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

    return redirect(url_for("projects")))
@app.route("/projects/edit/<int:project_id>", methods=["GET", "POST"])
def edit_project(project_id):

    conn = get_db()

    project = conn.execute(
        "SELECT * FROM projects WHERE id = ?",
        (project_id,)
    ).fetchone()

    if request.method == "POST":

        name = request.form["name"]
        description = request.form["description"]
        technology = request.form["technology"]

        conn.execute(
            """
            UPDATE projects
            SET name = ?, description = ?, technology = ?
            WHERE id = ?
            """,
            (name, description, technology, project_id)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("projects"))

    conn.close()

    return render_template(
        "edit_project.html",
        project=project
    )


@app.route("/projects/delete/<int:project_id>")
def delete_project(project_id):

    conn = get_db()

    conn.execute(
        "DELETE FROM projects WHERE id = ?",
        (project_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("projects"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)