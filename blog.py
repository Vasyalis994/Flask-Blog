from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user 
from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_security-key'

login_manager = LoginManager(app)
login_manager.login_view = 'login'

connection = sqlite3.connect("sqlite.db", check_same_thread=False)
cursor = connection.cursor()
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
     user = cursor.execute(
         'SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()
     if user is not None:
        return User(user[0], user[1], user[2])
     return None

@app.route("/login/", methods=["GET","POST"])
def login():
    connection = sqlite3.connect("sqlite.db",)
    cursor = connection.cursor()
    if request.method == "POST":
            username = request.form["username"]
            password = request.form["password"]
            user = cursor.execute(
                'SELECT * FROM user WHERE username = ?', (username,)
            ).fetchone()
            if user and User(user[0], user[1], user[2]).check_password(password):
                login_user(User(user[0], user[1], user[2]))
                return redirect(url_for("index"))
            else:
                return render_template("login.html", message="Invalin username of password")
    return render_template('login.html',)

@app.route("/logout/")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/register/", methods=["GET","POST"])
def register():
    connection = sqlite3.connect("sqlite.db",)
    cursor = connection.cursor()
    try:
        if request.method == "POST":
            username = request.form["username"]
            password = request.form["password"]
            email = request.form["email"]
            cursor.execute(
                "INSERT INTO user (username, password_hash, email) VALUES (?,?,?)",
                (username, generate_password_hash(password), email)
            )
            connection.commit()
            print("Регистрация прошла успешно!")
            return redirect(url_for('login'))
    except sqlite3.IntegrityError:
        print("Username already exists!")
        return render_template("register.html",
                           message="Username already exists!")
    return render_template("register.html",)



@app.route("/")
def index():
    connection = sqlite3.connect("sqlite.db")
    cursor = connection.cursor()

    cursor.execute(''' SELECT
           post.id, post.title, post.content, post.author_id, user.username, COUNT (like.id) AS likes
           FROM
                post
           JOIN
                user ON post.author_id = user.id
           LEFT JOIN
                like ON post.id = like.post_id
           GROUP BY
                post.id, post.title, post.content, post.author_id, user.username
        ''')
    result = cursor.fetchall()
    print(result)
    posts=[]
    for post in reversed(result):
        posts.append({"id":post[0], "title":post[1], "content":post[2], "author_id": post[3], "username": post[4], "likes": post[5]})
        if current_user.is_authenticated:
            cursor.execute(
                "SELECT post_id FROM like WHERE user_id = ?", (current_user.id,)
            )
            likes_result = cursor.fetchall()
            liked_posts = []
            for like in likes_result:
                liked_posts.append(like[0])
            posts[-1]["liked_posts"] = liked_posts
    context = {'posts':posts}
    return render_template("indexblog.html",**context)


@app.route("/me/")
def aks():
    context = {
        "title": "My blog",
        "name": "Lisa",
    }
    return render_template("indexblog.html", **context)


@app.route("/add/", methods=["GET","POST"])
@login_required
def add_post():
    connection = sqlite3.connect("sqlite.db", check_same_thread=False)
    cursor = connection.cursor()

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        cursor.execute(
            "INSERT INTO post (title, content, author_id) VALUES (?,?,?)",
            (title, content, current_user.id)
        )
        connection.commit()
        return redirect(url_for("index"))
    return render_template("add_post.html")

@app.route('/post/<post_id>', methods=["GET","POST"])
def post(post_id):
    connection = sqlite3.connect("sqlite.db")
    cursor = connection.cursor()

    if request.method == "POST":
        comment = request.form ["comment"]
        cursor.execute("insert into comments (user_id, post_id, comment) values (?,?,?)",(current_user.id, post_id, comment))
        connection.commit ()
        return redirect (url_for("post", post_id = post_id))

    else:
        result = cursor.execute(
            "SELECT * FROM post WHERE id=? ", (post_id,)
        ).fetchone()

        comments = cursor.execute(
            '''
            SELECT comments.id, comments.comment, comments.user_id, user.username
            FROM comments
            JOIN user ON comments.user_id = user.id
            WHERE comments.post_id = ?
            ''',
            (post_id,)).fetchall()
        print (comments)
        comment_list = []
        for comment in comments:
            comment_list.append({"id": comment[0], "text": comment[1], "user_id": comment[2], "username": comment[3]})

        context = {"post": {"id": result[0], "title": result[1], "content": result[2], "author_id": result[3], "comments": comment_list}}

        return render_template("postt.html",**context)

@app.route("/delete/<int:post_id>", methods=["POST"])
@login_required
def delete_post(post_id):
    connection = sqlite3.connect("sqlite.db", )
    cursor = connection.cursor()
    post = cursor.execute("SELECT * FROM post WHERE id = ?",
                           (post_id,)).fetchone()
    print(post, post[3])
    if post and post[3] == current_user.id:
        cursor.execute("DELETE FROM post WHERE id = ?", (post_id,))
        connection.commit()
        return redirect(url_for("index"))
    else:
        return redirect(url_for("index"))

def user_is_liking(post_id):
    like = cursor.execute(
        'SELECT * FROM like WHERE user_id = ? AND post_id = ?',
        (current_user.id, post_id)).fetchone()
    return bool(like)

@app.route('/like/<int:post_id>')
@login_required
def like_post(post_id):
    connection = sqlite3.connect("sqlite.db", )
    cursor = connection.cursor()
    post = cursor.execute("SELECT * FROM post WHERE id = ?",
                          (post_id,)).fetchone()
    if post:
        if user_is_liking(post_id):
            cursor.execute(
                'DELETE FROM like WHERE user_id = ? AND post_id = ?',
                (current_user.id,post_id))
            connection.commit()
            print("You unliked this post")
        else:
            cursor.execute(
                'INSERT INTO like (user_id, post_id) VALUES (?,?)',
                (current_user.id, post_id))
            connection.commit()
            print("You liked this post")
        return redirect(url_for("index"))
    return "Post not found", 404

if __name__ == "__main__":
    app.run(debug=True)
