import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, jsonify, abort
from workout import app, db, bcrypt, mail
from workout.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm, RequestResetForm, ResetPasswordForm, ConfirmPasswordForm
from workout.models import User, Post, Followers
from flask_login import login_user, current_user, logout_user, login_required
from datetime import date
from sqlalchemy.sql.expression import func
from flask_mail import Message

#Renders the home template
@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html')

#Renders a partial that informs a user who is creating an account or editing their username if the username is taken or not
@app.route("/username", methods=["POST"])
def username():
    found = False
    too_short = False
    too_long = False
    check_username = User.query.filter_by(username = request.form['username']).first()
    if check_username:
        found = True
    if len(request.form['username']) < 2:
        too_short = True
    if len(request.form['username']) > 20:
        too_long = True
    return render_template("partials/username.html", found=found, too_short=too_short, too_long=too_long, check_username=check_username)

#Renders a partial that informs a user who is creating an account or editing their email if the email is taken or not
@app.route("/email", methods=["POST"])
def email():
    found = False
    check_email = User.query.filter_by(email=request.form['email']).first()
    if check_email:
        found = True
    return render_template("partials/email.html", found=found)

@app.route("/usersearch", methods=["POST"])
def usersearch():
    no_users = False
    show = True
    if request.form['usersearch'] == "":
        show = False
        return render_template("partials/user_search.html", show=show)
    users = User.query.filter(User.username.like("%" + request.form['usersearch'] + "%")).limit(8)
    if users.all() == [] and request.form['usersearch'] != "":
        no_users = True
    return render_template("partials/user_search.html", users=users, show=show, no_users=no_users)

#Render a template to let a user sign up
@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, first_name=form.first_name.data, last_name=form.last_name.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f'Account Created for {form.username.data} Successfully!', 'success')
        login_user(user)
        return redirect(url_for('home'))
    return render_template('register.html', title='Register', form=form)

#Render a template to log a user in
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

#Render a template of all the posts in the database
@app.route("/feed")
def feed():
    page = request.args.get('page', 1, type=int)
    today_date = date.today()
    users = User.query.all()
    posts = Post.query.order_by(Post.date_posted.desc()).all()
    following = Followers.query.filter_by(follower_id=current_user.id)
    return render_template('feed.html', title='Feed', posts=posts, today_date=today_date, following=following, users=users)

#function to save a picture the user uploads to the data base
def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn

#Render a template of current users account and information that editable 
@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    # Lists for followers and following
    follower_list = []
    following_list = []

    # Getting followers and following and appending them to their respective lists
    followers = Followers.query.filter_by(user_id=current_user.id).all()
    following = Followers.query.filter_by(follower_id=current_user.id).all()
    for follower in followers:
        user = User.query.filter_by(id=follower.follower_id).first()
        follower_list.append(user)
    for follow in following:
        user = User.query.filter_by(id=follow.user_id).first()
        following_list.append(user)
    
    #Getting number of followers and follows
    follower_count = len(follower_list)
    follow_count = len(following_list)

    #Declaring some variables for functionality
    name_length = len(current_user.username)
    page = request.args.get('page', 1, type=int)
    today_date = date.today()
    posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.date_posted.desc()).paginate(page=page, per_page=2)
    form = UpdateAccountForm()

    #For updating user info on post method or for populating data with current data if get method
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file, form=form, posts=posts, today_date=today_date, name_length=name_length, follower_list=follower_list, follower_count=follower_count, following_list=following_list, follow_count=follow_count)

#Render an uneditable template of other users 
@app.route("/account/<int:user_id>", methods=['GET', 'POST'])
def foreign_account(user_id):
    name_length = 0
    already_following = False
    if not current_user.is_anonymous:
        if user_id == current_user.id:
            return redirect("/account")
        check_follow = Followers.query.filter_by(user_id=user_id, follower_id=current_user.id).first()
        if check_follow:
            already_following = True
    
    # Lists for followers and following
    follower_list = []
    following_list = []

    # Getting followers and following and appending them to their respective lists
    followers = Followers.query.filter_by(user_id=user_id).all()
    following = Followers.query.filter_by(follower_id=user_id).all()
    for follower in followers:
        user = User.query.filter_by(id=follower.follower_id).first()
        follower_list.append(user)
    for follow in following:
        user = User.query.filter_by(id=follow.user_id).first()
        following_list.append(user)

    #Getting number of followers and follows
    follower_count = len(follower_list)
    follow_count = len(following_list)

    page = request.args.get('page', 1, type=int)
    today_date = date.today()
    user = User.query.get_or_404(user_id)
    name_length = len(user.username)
    posts = Post.query.filter_by(user_id=user_id).order_by(Post.date_posted.desc()).paginate(page=page, per_page=2)
    image_file = url_for('static', filename='profile_pics/' + user.image_file)
    return render_template('foreign_account.html', title=user.username, user=user, image_file=image_file, posts=posts, today_date=today_date, already_following=already_following, follower_list=follower_list, following_list=following_list, follower_count=follower_count, follow_count=follow_count, name_length=name_length)

#Process a follow request
@app.route("/follow/user/<id>", methods=["POST"])
def new_follow(id):
    if current_user.is_anonymous:
        flash('You must log in to follow users', 'info')
        return redirect("/login")
    follow_relationship = Followers.query.filter_by(user_id=id, follower_id=current_user.id).first()
    if follow_relationship or int(id) == current_user.id:
        print('nope')
        return redirect("/home")
    new_follow_relationship = Followers(user_id=id, follower_id=current_user.id)
    db.session.add(new_follow_relationship)
    db.session.commit()
    return redirect("/account/" + id)

#Process an unfollow request
@app.route("/unfollow/user/<id>", methods=["POST"])
@login_required
def unfollow(id):
    get_follow = Followers.query.filter_by(user_id=id, follower_id=current_user.id).first()
    if get_follow:
        db.session.delete(get_follow)
        db.session.commit()
        return redirect("/account/" + id)
    else:
        flash('You can not unfollow someone you dont follow', 'danger')
        return redirect("/home")

#Render a template to create a post and save it to database
@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, comments=form.comments.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created and posted.', 'success')
        return redirect(url_for('feed'))
    return render_template('create_post.html', title='New Post', form=form, legend='New Post')

#Render a template to show a specific post
@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def post(post_id):
    today_date = date.today()
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post, today_date=today_date)

#Route to let a user update their post
@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.comments = form.comments.data
        db.session.commit()
        flash('Your post has been updated.', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
        form.comments.data = post.comments
    return render_template('create_post.html', title='Update Post', form=form, legend='Update Post')

#Post route to process deleting a post
@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted.', 'success')
    return redirect(url_for('feed'))

#Function to create and send an email if a user request a link to reset forgotten password
def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request', sender='noreply@demo.com', recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request then simply ignore this email and no changes will be made
'''
    mail.send(msg)

#Function to send an email notifying user that password has been reset
def send_info_email(user):
    msg = Message('Password Reset Confirmed', sender='noreply@demo.com', recipients=[user.email])
    msg.body = f'''Your password has been reset.

If you did not do this, then request a password change by visiting this link http://localhost:5000/reset_password
'''
    mail.send(msg)

#Has user enter their email to prepare for email link
@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)

#Allows user to change password from token if they forgot current password
@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That token is either invalid or expired.', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        send_info_email(user)
        flash('Your password has been updated, you are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)

#Has user confirm their password to get token for resetting password
@app.route("/confirm_password", methods=['GET', 'POST'])
@login_required
def confirm_password():
    form = ConfirmPasswordForm()
    if form.validate_on_submit():
        if bcrypt.check_password_hash(current_user.password, form.password.data):
            token = current_user.get_reset_token()
            return redirect(url_for('change_password', token=token))
        flash('That password doesnt match your current password.', 'danger')
    return render_template('confirm_password.html', title='Reset Password', form=form)

#Allows user to change password while being logged in
@app.route("/change_password/<token>", methods=['GET', 'POST'])
@login_required
def change_password(token):
    user = current_user.verify_reset_token(token)
    if user is None:
        flash('That token is either invalid or expired.', 'warning')
        return redirect(url_for('confirm_password'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        send_info_email(user)
        flash('Your password has been updated', 'success')
        return redirect(url_for('home'))
    return render_template('reset_token.html', title='Reset Password', form=form)

@app.route("/find_users", methods=['GET', 'POST'])
def find_users():
    users = User.query.all()
    return render_template('find_users.html', title='Find Users', users=users)

#Logout a logged in user
@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))