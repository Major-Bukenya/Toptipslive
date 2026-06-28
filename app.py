from flask import Flask, render_template, redirect, url_for, request, flash, session
from models import db, User, Tip
from config import Config
from datetime import datetime, timedelta
import functools

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# Context processor to make current_user available in all templates
@app.context_processor
def inject_current_user():
    return {'current_user': get_current_user()}

# Custom login required decorator
def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Custom admin required decorator
def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None or not user.is_admin:
            flash('Admin privileges required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Get current user from session
def get_current_user():
    if 'user_id' in session and 'session_token' in session:
        user = User.query.get(session['user_id'])
        if user and user.session_token == session['session_token'] and user.is_session_valid():
            return user
    # If session is invalid, clear it
    session.clear()
    return None

# Create database tables and admin user
with app.app_context():
    db.create_all()
    # Create admin user if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@olbg.com', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

# Routes
@app.route('/')
def index():
    tips = Tip.query.order_by(Tip.created_at.desc()).limit(6).all()
    return render_template('index.html', tips=tips)

@app.route('/login', methods=['GET', 'POST'])
def login():
    user = get_current_user()
    if user:
        if user.is_admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session_token = user.generate_session_token()
            db.session.commit()
            
            session['user_id'] = user.id
            session['session_token'] = session_token
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            
            next_page = request.args.get('next')
            if user.is_admin:
                return redirect(next_page or url_for('admin_dashboard'))
            else:
                return redirect(next_page or url_for('user_dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    user = get_current_user()
    if user:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    user = get_current_user()
    if user:
        user.session_token = None
        user.session_expiry = None
        db.session.commit()
    
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/user/dashboard')
@login_required
def user_dashboard():
    # Regular users can only view tips, not create them
    tips = Tip.query.order_by(Tip.created_at.desc()).all()
    return render_template('user/dashboard.html', tips=tips)

@app.route('/add_tip', methods=['POST'])
@login_required
@admin_required  # Only admins can add tips
def add_tip():
    user = get_current_user()
    league = request.form.get('league')
    match = request.form.get('match')
    bet_type = request.form.get('bet_type')
    odds = float(request.form.get('odds'))
    stake = int(request.form.get('stake'))
    reasoning = request.form.get('reasoning')
    match_time_str = request.form.get('match_time')
    
    match_time = datetime.strptime(match_time_str, '%Y-%m-%dT%H:%M') if match_time_str else datetime.utcnow()
    
    tip = Tip(
        league=league,
        match=match,
        bet_type=bet_type,
        odds=odds,
        stake=stake,
        reasoning=reasoning,
        match_time=match_time,
        user_id=user.id
    )
    
    db.session.add(tip)
    db.session.commit()
    
    flash('Tip added successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/update_tip/<int:tip_id>', methods=['POST'])
@login_required
@admin_required  # Only admins can update tips
def update_tip(tip_id):
    user = get_current_user()
    tip = Tip.query.get_or_404(tip_id)
    
    tip.league = request.form.get('league')
    tip.match = request.form.get('match')
    tip.bet_type = request.form.get('bet_type')
    tip.odds = float(request.form.get('odds'))
    tip.stake = int(request.form.get('stake'))
    tip.reasoning = request.form.get('reasoning')
    tip.result = request.form.get('result')
    
    match_time_str = request.form.get('match_time')
    if match_time_str:
        tip.match_time = datetime.strptime(match_time_str, '%Y-%m-%dT%H:%M')
    
    db.session.commit()
    
    flash('Tip updated successfully!', 'success')
    return redirect(url_for('admin_tips'))

@app.route('/delete_tip/<int:tip_id>')
@login_required
@admin_required  # Only admins can delete tips
def delete_tip(tip_id):
    tip = Tip.query.get_or_404(tip_id)
    
    db.session.delete(tip)
    db.session.commit()
    
    flash('Tip deleted successfully!', 'success')
    return redirect(url_for('admin_tips'))

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    total_users = User.query.count()
    total_tips = Tip.query.count()
    pending_tips = Tip.query.filter_by(result='pending').count()
    
    return render_template('admin/dashboard.html', 
                          total_users=total_users, 
                          total_tips=total_tips, 
                          pending_tips=pending_tips)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/tips')
@login_required
@admin_required
def admin_tips():
    tips = Tip.query.order_by(Tip.created_at.desc()).all()
    return render_template('admin/tips.html', tips=tips)

if __name__ == '__main__':
    app.run(debug=True)