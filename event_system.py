from flask import Flask, render_template_string, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import datetime

app = Flask(__name__)
app.secret_key = 'secretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ---------- MODELS ----------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    date = db.Column(db.DateTime)
    location = db.Column(db.String(200))

class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    registered_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------- ROUTES ----------
@app.route('/')
def index():
    events = Event.query.all()
    return render_template_string("""
    <h1>Event List</h1>
    {% for e in events %}
        <p><a href="{{ url_for('event_detail', event_id=e.id) }}">{{ e.title }}</a> - {{ e.date.strftime('%Y-%m-%d') }}</p>
    {% endfor %}
    <br>
    {% if current_user.is_authenticated %}
        <a href="{{ url_for('my_registrations') }}">My Registrations</a> |
        <a href="{{ url_for('logout') }}">Logout</a>
    {% else %}
        <a href="{{ url_for('login') }}">Login</a>
    {% endif %}
    """, events=events)

@app.route('/event/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    registered = False
    if current_user.is_authenticated:
        registered = Registration.query.filter_by(user_id=current_user.id, event_id=event.id).first()
    return render_template_string("""
    <h2>{{ event.title }}</h2>
    <p>{{ event.description }}</p>
    <p>Location: {{ event.location }}</p>
    <p>Date: {{ event.date.strftime('%Y-%m-%d') }}</p>
    {% if current_user.is_authenticated %}
        {% if registered %}
            <p>You are registered. <a href="{{ url_for('cancel_registration', event_id=event.id) }}">Cancel</a></p>
        {% else %}
            <a href="{{ url_for('register_event', event_id=event.id) }}">Register</a>
        {% endif %}
    {% else %}
        <p><a href="{{ url_for('login') }}">Login</a> to register</p>
    {% endif %}
    <br><a href="{{ url_for('index') }}">Back</a>
    """, event=event, registered=registered)

@app.route('/register/<int:event_id>')
@login_required
def register_event(event_id):
    if not Registration.query.filter_by(user_id=current_user.id, event_id=event_id).first():
        reg = Registration(user_id=current_user.id, event_id=event_id)
        db.session.add(reg)
        db.session.commit()
        flash("Registered successfully!")
    return redirect(url_for('my_registrations'))

@app.route('/cancel/<int:event_id>')
@login_required
def cancel_registration(event_id):
    reg = Registration.query.filter_by(user_id=current_user.id, event_id=event_id).first()
    if reg:
        db.session.delete(reg)
        db.session.commit()
        flash("Registration cancelled.")
    return redirect(url_for('my_registrations'))

@app.route('/my-registrations')
@login_required
def my_registrations():
    regs = Registration.query.filter_by(user_id=current_user.id).all()
    return render_template_string("""
    <h2>My Registrations</h2>
    {% for r in regs %}
        <p>{{ r.event.title }} - <a href="{{ url_for('cancel_registration', event_id=r.event.id) }}">Cancel</a></p>
    {% else %}
        <p>No registrations.</p>
    {% endfor %}
    <br><a href="{{ url_for('index') }}">Back</a>
    """, regs=regs)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(username=request.form['username']).first()
        if u and u.password == request.form['password']:
            login_user(u)
            return redirect(url_for('index'))
        flash("Invalid credentials.")
    return render_template_string("""
    <h2>Login</h2>
    <form method="POST">
        Username: <input name="username"><br>
        Password: <input name="password" type="password"><br>
        <button type="submit">Login</button>
    </form>
    <p><a href="{{ url_for('register') }}">No account? Register</a></p>
    """)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if User.query.filter_by(username=request.form['username']).first():
            flash("Username taken.")
        else:
            u = User(username=request.form['username'], password=request.form['password'])
            db.session.add(u)
            db.session.commit()
            flash("Registered. You can now login.")
            return redirect(url_for('login'))
    return render_template_string("""
    <h2>Register</h2>
    <form method="POST">
        Username: <input name="username"><br>
        Password: <input name="password" type="password"><br>
        <button type="submit">Register</button>
    </form>
    <p><a href="{{ url_for('login') }}">Back to login</a></p>
    """)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ---------- DATABASE INIT ----------
def init_db():
    db.create_all()
    if not Event.query.first():
        db.session.add_all([
            Event(title="Tech Conference", description="Annual tech conf", location="Bangalore", date=datetime.datetime(2025, 7, 15)),
            Event(title="AI Summit", description="Talks on AI and ML", location="Hyderabad", date=datetime.datetime(2025, 8, 10)),
        ])
        db.session.commit()

# ---------- MAIN ----------
if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)
