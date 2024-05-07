from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
from functools import wraps

app = Flask(__name__)

app.secret_key = 'ahpoiju'
app.config['MYSQL_USER'] = 'root'  # Nazwa użytkownika MySQL
app.config['MYSQL_PASSWORD'] = ''  # Hasło do MySQL
app.config['MYSQL_DB'] = 'user'  # Nazwa bazy danych
app.config['MYSQL_HOST'] = 'localhost'  # Gdzie znajduje się serwer MySQL
app.config['MYSQL_PORT'] = 3307  # Domyślny port MySQL w XAMPP

mysql = MySQL(app)


# Wrapper do autoryzacji użytkowników
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' not in session:
            flash("You need to log in to access this page.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('email') != 'admin@system.com':
            flash("You are not authorized to access this page.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST':
        if 'email' in request.form and 'password' in request.form:
            email = request.form['email']
            password = request.form['password']

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM user WHERE email = %s AND password = %s', (email, password))
            user = cursor.fetchone()

            if user:
                session['loggedin'] = True
                session['userid'] = user['userid']
                session['name'] = user['name']
                session['email'] = user['email']
                flash("Logged in successfully!", "success")

                if email == 'admin@system.com':
                    return redirect(url_for('admin'))

                return redirect(url_for('user'))

            else:
                message = 'Incorrect email or password'
    return render_template('login.html', message=message)


@app.route('/user')
@login_required
def user():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM post WHERE user_id = %s", (session['userid'],))
    posts = cursor.fetchall()
    return render_template('user.html', posts=posts)


@app.route('/logout')
@login_required
def logout():
    session.pop('loggedin', None)
    session.pop('userid', None)
    session.pop('name', None)
    session.pop('email', None)
    flash("Logged out successfully.", "success")
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
        account = cursor.fetchone()

        if account:
            message = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            message = 'Invalid email address!'
        elif not name or not password or not email:
            message = 'Please fill out all fields!'
        else:
            cursor.execute("INSERT INTO user (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
            mysql.connection.commit()
            flash("Successfully registered.", "success")
            return redirect(url_for('login'))

    return render_template('register.html', message=message)


@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        if user_id:
            cursor.execute("DELETE FROM user WHERE userid = %s", (user_id,))
            mysql.connection.commit()
            flash("User deleted successfully.", "success")

    cursor.execute("""
        SELECT post.id, post.content, user.name as user_name
        FROM post
        JOIN user ON post.user_id = user.userid
    """)
    posts = cursor.fetchall()

    return render_template('admin.html', posts=posts)


@app.route('/post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        content = request.form.get("content")
        if content:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("INSERT INTO post (content, user_id) VALUES (%s, %s)", (content, session['userid']))
            mysql.connection.commit()
            flash("Post created successfully.", "success")
            return redirect(url_for('user'))

    return render_template('create_post.html')


@app.route('/post/delete/<int:post_id>', methods=['GET'])
@login_required
def delete_post(post_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM post WHERE id = %s", (post_id,))
    post = cursor.fetchone()

    if not post:
        flash("Post not found.", "danger")
        return redirect(url_for('user'))


    if session.get('email') != 'admin@system.com' and post['user_id'] != session['userid']:
        flash("You are not authorized to delete this post.", "danger")
        return redirect(url_for('user'))

    # Usuń post
    cursor.execute("DELETE FROM post WHERE id = %s", (post_id,))
    mysql.connection.commit()

    flash("Post deleted successfully.", "success")
    if session.get('email') == 'admin@system.com':
        return redirect(url_for('admin'))
    else:
        return redirect(url_for('user'))


if __name__ == "__main__":
    app.run(debug=True)