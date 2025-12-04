from flask import Flask, render_template, request, url_for, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user, login_required
from functools import wraps
from datetime import datetime
from flask_migrate import Migrate
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Arhat-Machine'
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:Donaterteam002@localhost/kland_db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Настройки для загрузки файлов
app.config['UPLOAD_FOLDER'] = 'static/images/uploads/teachers'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB максимум
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Создай папку если ее нет
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
csrf = CSRFProtect(app)
login_manager.login_view = "login"

# Упрощенные формы без email_validator
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Войти')

class RegistrationForm(FlaskForm):
    name = StringField('Имя', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Подтвердите пароль', validators=[DataRequired()])
    submit = SubmitField('Зарегистрироваться')

class CourseApplicationForm(FlaskForm):
    course_type = StringField('Тип курса', validators=[DataRequired()])
    name = StringField('Имя', validators=[DataRequired()])
    phone = StringField('Телефон', validators=[DataRequired()])
    submit = SubmitField('Отправить заявку')

class ContactForm(FlaskForm):
    name = StringField('Имя', validators=[DataRequired()])
    phone = StringField('Телефон', validators=[DataRequired()])
    message = StringField('Сообщение', validators=[DataRequired()])
    submit = SubmitField('Отправить')

class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="student")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)
    
    @property
    def is_admin(self):
        return self.role == 'admin'

class CourseApplication(db.Model):
    __tablename__ = 'course_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    course_type = db.Column(db.String(20), nullable=False)
    applicant_name = db.Column(db.String(100), nullable=False)
    applicant_phone = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='new')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_published = db.Column(db.Boolean, default=True)

class AdmissionPeriod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    application_start = db.Column(db.String(50), nullable=False)
    application_end = db.Column(db.String(50), nullable=False)
    studies_start = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Messages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    message = db.Column(db.String(800), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    photo = db.Column(db.String(200))
    tags = db.Column(db.String(300))
    is_founder = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_tags_list(self):
        return [tag.strip() for tag in self.tags.split(',')] if self.tags else []

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return "Доступ запрещён!", 403
        return f(*args, **kwargs)
    return decorated

# Новости для пользователей
@app.route('/news')
def news():
    news_list = News.query.filter_by(is_published=True).order_by(News.created_at.desc()).all()
    return render_template('news.html', news_list=news_list)

@app.route('/news/<int:news_id>')
def news_detail(news_id):
    news_item = News.query.get_or_404(news_id)
    return render_template('news_detail.html', news=news_item)

# Админка для новостей
@app.route('/admin/news')
@admin_required
def admin_news():
    return redirect(url_for('admin_panel'))

@app.route('/admin/news/add', methods=['GET', 'POST'])
@admin_required
def add_news():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        image_url = request.form.get('image_url', '')
        is_published = 'is_published' in request.form
        
        new_news = News(
            title=title, 
            content=content, 
            image_url=image_url,
            is_published=is_published
        )
        db.session.add(new_news)
        db.session.commit()
        
        flash('Новость успешно добавлена!', 'success')
        return redirect(url_for('admin_panel'))
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/news/edit/<int:news_id>', methods=['GET', 'POST'])
@admin_required
def edit_news(news_id):
    news_item = News.query.get_or_404(news_id)
    
    if request.method == 'POST':
        news_item.title = request.form['title']
        news_item.content = request.form['content']
        news_item.image_url = request.form.get('image_url', '')
        news_item.is_published = 'is_published' in request.form
        
        db.session.commit()
        flash('Новость успешно обновлена!', 'success')
        return redirect(url_for('admin_panel'))
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/news/delete/<int:news_id>')
@admin_required
def delete_news(news_id):
    news_item = News.query.get_or_404(news_id)
    db.session.delete(news_item)
    db.session.commit()
    flash('Новость успешно удалена!', 'success')
    return redirect(url_for('admin_panel'))

# Управление сроками поступления в Корею
@app.route('/admin/admission-periods')
@admin_required
def admin_admission_periods():
    periods = AdmissionPeriod.query.order_by(AdmissionPeriod.created_at.desc()).all()
    users = Users.query.all()
    applications = CourseApplication.query.order_by(CourseApplication.created_at.desc()).all()
    news_list = News.query.order_by(News.created_at.desc()).all()
    
    return render_template('admin.html', 
                         users=users, 
                         applications=applications, 
                         news_list=news_list,
                         admission_periods=periods,
                         active_tab='korea-admission')

@app.route('/admin/admission-periods/add', methods=['POST'])
@admin_required
def add_admission_period():
    name = request.form.get('name')
    application_start = request.form.get('application_start')
    application_end = request.form.get('application_end')
    studies_start = request.form.get('studies_start')
    is_active = request.form.get('is_active') == 'on'
    
    period = AdmissionPeriod(
        name=name,
        application_start=application_start,
        application_end=application_end,
        studies_start=studies_start,
        is_active=is_active
    )
    
    db.session.add(period)
    db.session.commit()
    
    flash('Период поступления добавлен', 'success')
    return redirect(url_for('admin_admission_periods'))

@app.route('/admin/admission-periods/edit/<int:id>', methods=['POST'])
@admin_required
def edit_admission_period(id):
    period = AdmissionPeriod.query.get_or_404(id)
    period.name = request.form.get('name')
    period.application_start = request.form.get('application_start')
    period.application_end = request.form.get('application_end')
    period.studies_start = request.form.get('studies_start')
    period.is_active = request.form.get('is_active') == 'on'
    db.session.commit()
    
    flash('Период поступления обновлен', 'success')
    return redirect(url_for('admin_admission_periods'))

@app.route('/admin/admission-periods/delete/<int:id>', methods=['POST'])
@admin_required
def delete_admission_period(id):
    period = AdmissionPeriod.query.get_or_404(id)
    db.session.delete(period)
    db.session.commit()
    
    flash('Период поступления удален', 'success')
    return redirect(url_for('admin_admission_periods'))

# Управление учителями
@app.route('/admin/teachers', methods=['GET', 'POST'])
@admin_required
def admin_teachers():
    # Обработка добавления нового учителя
    if request.method == 'POST' and 'add_teacher' in request.form:
        name = request.form.get('name')
        role = request.form.get('role')
        tags = request.form.get('tags')
        is_founder = 'is_founder' in request.form
        order = request.form.get('order', 0, type=int)
        
        # Обработка загрузки фото
        photo_filename = None
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and photo.filename != '' and allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                # Добавляем timestamp чтобы избежать конфликтов имен
                import time
                timestamp = str(int(time.time()))
                filename = f"{timestamp}_{filename}"
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                photo.save(photo_path)
                photo_filename = f"uploads/teachers/{filename}"
        
        teacher = Teacher(
            name=name,
            role=role,
            tags=tags,
            photo=photo_filename,
            is_founder=is_founder,
            order=order
        )
        
        db.session.add(teacher)
        db.session.commit()
        flash('Учитель успешно добавлен', 'success')
        return redirect(url_for('admin_teachers'))
    
    # Обработка редактирования учителя
    if request.method == 'POST' and 'edit_teacher' in request.form:
        teacher_id = request.form.get('teacher_id')
        teacher = Teacher.query.get(teacher_id)
        
        if teacher:
            teacher.name = request.form.get('edit_name')
            teacher.role = request.form.get('edit_role')
            teacher.tags = request.form.get('edit_tags')
            teacher.is_founder = 'edit_is_founder' in request.form
            teacher.order = request.form.get('edit_order', 0, type=int)
            
            # Обработка загрузки фото при редактировании
            if 'edit_photo' in request.files:
                photo = request.files['edit_photo']
                if photo and photo.filename != '' and allowed_file(photo.filename):
                    filename = secure_filename(photo.filename)
                    import time
                    timestamp = str(int(time.time()))
                    filename = f"{timestamp}_{filename}"
                    photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    photo.save(photo_path)
                    teacher.photo = f"uploads/teachers/{filename}"
            
            db.session.commit()
            flash('Учитель успешно обновлен', 'success')
        
        return redirect(url_for('admin_teachers'))
    
    teachers = Teacher.query.order_by(Teacher.order, Teacher.name).all()
    users = Users.query.all()
    applications = CourseApplication.query.order_by(CourseApplication.created_at.desc()).all()
    news_list = News.query.order_by(News.created_at.desc()).all()
    periods = AdmissionPeriod.query.order_by(AdmissionPeriod.created_at.desc()).all()
    message_entry = Messages.query.all()
    
    return render_template('admin.html', 
                         users=users, 
                         applications=applications, 
                         news_list=news_list,
                         admission_periods=periods,
                         message_entry=message_entry,
                         teachers=teachers,
                         active_tab='teachers')

@app.route('/admin/teachers/delete/<int:id>')
@admin_required
def delete_teacher(id):
    teacher = Teacher.query.get_or_404(id)
    db.session.delete(teacher)
    db.session.commit()
    flash('Учитель успешно удален', 'success')
    return redirect(url_for('admin_teachers'))

# Страница поступления в Корею
@app.route('/corey')
def corey():
    periods = AdmissionPeriod.query.filter_by(is_active=True).all()
    return render_template('corey.html', admission_periods=periods)

@app.route('/admission-korea')
def admission_korea():
    return redirect(url_for('corey'))

@app.route('/admin')
@admin_required
def admin_panel():
    users = Users.query.all()
    applications = CourseApplication.query.order_by(CourseApplication.created_at.desc()).all()
    news_list = News.query.order_by(News.created_at.desc()).all()
    periods = AdmissionPeriod.query.order_by(AdmissionPeriod.created_at.desc()).all()
    message_entry = Messages.query.all()
    teachers = Teacher.query.order_by(Teacher.order, Teacher.name).all()
    
    return render_template('admin.html', 
                         users=users, 
                         applications=applications, 
                         news_list=news_list,
                         admission_periods=periods,
                         message_entry=message_entry,
                         teachers=teachers)

@app.route('/update-status', methods=['POST'])
@admin_required
def update_status():
    app_id = request.form.get('application_id')
    new_status = request.form.get('status')
    
    try:
        application = CourseApplication.query.get(app_id)
        if application and new_status in ['new', 'contacted', 'approved']:
            application.status = new_status
            db.session.commit()
            flash('✅ Статус обновлен', 'success')
        else:
            flash('❌ Ошибка обновления', 'error')
    except Exception as e:
        db.session.rollback()
        flash('❌ Ошибка обновления', 'error')
    
    return redirect(url_for('admin_panel'))

@app.route("/sign-up", methods=["GET", "POST"])
def sign_up():
    form = RegistrationForm()
    
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    
    if form.validate_on_submit():
        name = form.name.data.strip()
        email = form.email.data.lower().strip()
        password = form.password.data

        existing_user = Users.query.filter_by(email=email).first()
        if existing_user:
            flash("Этот email уже используется!", "error")
            return render_template('sign-up.html', form=form)

        try:
            user = Users(name=name, email=email, role='student')
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash("Регистрация успешна! Теперь войдите в систему.", "success")
            return redirect(url_for("login"))
            
        except Exception as e:
            db.session.rollback()
            flash("Произошла ошибка при регистрации. Попробуйте еще раз.", "error")

    return render_template("sign-up.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    
    if current_user.is_authenticated:
        flash("Вы уже авторизованы!", "info")
        return redirect(url_for("home"))
    
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        password = form.password.data

        user = Users.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Неверная почта или пароль", "error")
            return render_template("login.html", form=form)

        login_user(user)
        session['role'] = user.role
        session['user_id'] = user.id
        flash(f"Добро пожаловать, {user.name}!", "success")
        
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for("home"))

    return render_template("login.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("login"))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    universities = [
        "Kyungnam College", "Yeungnam University", "Kyungil University",
        "Konyang University", "Kyungin Women's University", "Kyung Hee University",
        "Busan University of Foreign Studies", "Kunjang University", "Kukje University", 
        "Chung Cheong University", "Cheongju University", "Youngsan University",
        "Daekyeung University"
    ]
    teachers = Teacher.query.filter_by(is_active=True).order_by(Teacher.order, Teacher.name).all()
    return render_template('about.html', universities=universities, teachers=teachers)

@app.route('/courses')
def courses():
    form = CourseApplicationForm()
    return render_template('courses.html', form=form)

@app.route('/apply-course', methods=['POST'])
def apply_course():
    form = CourseApplicationForm()
    if form.validate_on_submit():
        try:
            course_type = form.course_type.data
            name = form.name.data
            phone = form.phone.data
            
            new_app = CourseApplication(
                course_type=course_type,
                applicant_name=name,
                applicant_phone=phone
            )
            
            db.session.add(new_app)
            db.session.commit()
            
            course_name = "Корейский" if course_type == 'korean' else "Английский"
            flash(f'Заявка на {course_name} язык отправлена!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash('Ошибка отправки заявки', 'error')
    else:
        flash('Ошибка валидации формы', 'error')
    
    return redirect(url_for('courses'))

@app.route('/contackt', methods=['POST', 'GET'])
def contackt():
    form = ContactForm()
    if form.validate_on_submit():
        name = form.name.data
        phone = form.phone.data
        message = form.message.data

        message_entry = Messages(name=name, phone=phone, message=message)
        db.session.add(message_entry)
        db.session.commit()

        flash('Заявка успешно отправлена!', 'success')
        return redirect(url_for('contackt'))

    return render_template('contackt.html', form=form)

@app.route('/delete_message/<int:message_id>', methods=['POST'])
@admin_required
def delete_message(message_id):
    msg = Messages.query.get_or_404(message_id)
    db.session.delete(msg)
    db.session.commit()
    flash('Сообщение удалено', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/debug-periods')
def debug_periods():
    periods = AdmissionPeriod.query.all()
    result = []
    for p in periods:
        result.append({
            'id': p.id,
            'name': p.name,
            'is_active': p.is_active,
            'application_start': p.application_start,
            'application_end': p.application_end,
            'studies_start': p.studies_start
        })
    return {'periods': result}



# Создание таблиц при запуске
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
