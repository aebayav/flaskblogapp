from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps

#WTForms ile kullanıcı kayıt formu ve validatorlar
class RegisterForm(Form):
    name = StringField("İsminiz:",validators=[validators.Length(min=4,max=25),validators.optional()])
    username = StringField("Kullanıcı Adınız:",validators=[validators.input_required(),validators.Length(min=4,max=25)])
    email = StringField("E-posta adresiniz:",validators=[validators.Email(message="Lütfen geçerli bir e-posta adresi girin")])
    password = PasswordField("Şifrenizi girin(Minimum 8,Maksimum 20 karakter olabilir):",
    validators=[validators.DataRequired(),validators.length(min =8,max =20),validators.EqualTo(fieldname= "confirm",message = "Şifreler uyuşmuyor...")])
    confirm = PasswordField("Şifrenizi tekrar girin")
     

#WTForms ile login sayfası
class LoginForm(Form):
    username = StringField("Kullancı Adı")
    password = PasswordField("Şifreniz")


#Makale Form
class ArticleForm(Form):
    title = StringField("Makale Başlığı",validators=[validators.Length(min=5,max=100)])
    content = TextAreaField("Makale İçeriği",validators=[validators.Length(min=5)])


#MySql ve flask bağlantıları ayrıca mysql ile flaskın birbirine bağlanması
app = Flask(__name__)
app.secret_key = "blog"
app.config["MYSQL_HOST"] =  "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "blog_db"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)


#Dashboard decoratoru
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:

            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntelemek için giriş yapmanız gerekmektedir","danger")
            return redirect(url_for("login"))
    return decorated_function



#Kayıt sayfası
@app.route("/register",methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.username.data
        password = sha256_crypt.encrypt(form.password.data)
        
        cursor = mysql.connection.cursor()

        query = "Insert into users(name,username,email,password) VALUES(%s,%s,%s,%s)"

        cursor.execute(query,(name,username,email,password))
        mysql.connection.commit()
        cursor.close()
        flash("Başarıyla kaydoldunuz","success")

        return redirect(url_for("index"))
    else:
        return render_template("register.html",form = form)

    






#Ana sayfa
@app.route("/")
def index():
    return render_template("index.html")
#Hakkımda sayfası
@app.route("/about")
def about():
    return render_template("about.html")

#login işlemi
@app.route("/login",methods=["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()

        query = "Select * From users where username = %s"

        result = cursor.execute(query,(username,))
        if result >0 :
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                session["logged_in"] = True
                session["username"] = username

                flash("Başarıyla giriş yaptınız.","success")
                return redirect(url_for("index"))
            else:
                flash("Hatalı şifre girdiniz.","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı bulunmamaktadır.","danger")
            return redirect(url_for("login"))
    
    return render_template("login.html", form = form)

#Logout işlemi
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

#Dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    query = "Select * From articles where author = %s"
    result = cursor.execute(query,(session["username"],))
    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles = articles)
    else:
        
        return render_template("dashboard.html")
    

#Makale Oluştur
@app.route("/addarticle",methods=["GET","POST"])
@login_required
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data
        cursor = mysql.connection.cursor()

        query = "Insert Into Articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(query,(title,session["username"],content))

        mysql.connection.commit()
        cursor.close()
        flash("Makale başarıyla yayınlandı","success")
        return redirect(url_for("dashboard"))


    return render_template("addarticle.html",form = form)


#Makale Sil
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    query = "Select * from articles where author = %s and id = %s"
    result = cursor.execute(query,(session["username"],id))
    if result >0:
        query2 = "Delete from articles where id = %s"
        cursor.execute(query2,(id,))
        mysql.connection.commit()
        flash("Makale başarıyla silindi","success")
        return redirect(url_for("dashboard"))


    else:
        flash("Böyle bir makale bulunmuyor ya da bu işlem için yetkiye sahip değilsiniz","danger")
        return redirect(url_for("index"))

#Makale Güncelleme
@app.route("/edit/<string:id>",methods=["GET","POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        query = "Select * From articles where id = %s and author = %s"
        result = cursor.execute(query,(id,session["username"]))
        if result == 0:
            flash("Böyle bir makale bulunmamaktadır","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.content.data = article["content"]
            form.title.data = article["title"]
            return render_template("update.html", form = form)
    else:
        #POST REQUEST
        form = ArticleForm(request.form)
        newTitle = form.content.data
        newContent = form.title.data
        
        query2 = "Update articles set title = %s,content = %s where id = %s"

        cursor = mysql.connection.cursor()

        cursor.execute(query2,(newTitle,newContent,id))

        mysql.connection.commit()
        
        flash("Makale Başarıyla Güncellendi","success")
        return redirect(url_for("dashboard"))




            
            
        

    




#Makale Görüntüleme,
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()

    query = "Select * From articles"

    result = cursor.execute(query)

    if result > 0:
        articles = cursor.fetchall()

        return render_template("articles.html",articles = articles)
    else:
        flash("Herhangi yayınlanmış bir makale bulunmamaktadır","danger")
        return render_template("articles.html")

#Detay sayfası

@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    query = "Select * from articles where id = %s"
    result = cursor.execute(query,(id,))
    if result >0:
        article = cursor.fetchone()
        return render_template("article.html", article = article)
    else:
        return render_template("article.html")


#Arama URL
@app.route("/search", methods = ["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        query = "Select * from articles where title like '%" + keyword + "%'" 
        result = cursor.execute(query)
        if result == 0:
            flash("Bu kelimeyi içeren bir makale bulunmamaktadır...","warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html",articles = articles)




if __name__ == "__main__":
    app.run(debug=True)




