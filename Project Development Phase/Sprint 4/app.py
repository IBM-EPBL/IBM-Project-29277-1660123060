from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, SelectField, IntegerField
import ibm_db
from functools import wraps
from datetime import datetime, timedelta
import sendgrid
import os
from sendgrid.helpers.mail import Mail, Email, To, Content
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
app.secret_key = 'ceg1234'
dsn_hostname = "98538591-7217-4024-b027-8baa776ffad1.c3n41cmd0nqnrk39u98g.databases.appdomain.cloud" 
dsn_uid = "hgd72603"        
dsn_pwd = "qUt0VtWTanLWm4bJ"      

dsn_driver = "{IBM DB2 ODBC DRIVER}"
dsn_database = "bludb"            
dsn_port = "30875"                
dsn_protocol = "TCPIP"          
dsn_security = "SSL"              

dsn = (
    "DRIVER={0};"
    "DATABASE={1};"
    "HOSTNAME={2};"
    "PORT={3};"
    "PROTOCOL={4};"
    "UID={5};"
    "PWD={6};"
    "SECURITY={7};"
    "SSLServerCerificate=DigiCertGlobalRootCA.crt").format(dsn_driver, dsn_database, dsn_hostname, dsn_port, dsn_protocol, dsn_uid, dsn_pwd,dsn_security)

try:
    conn = ibm_db.connect(dsn,"","")
except:
    print("Unable to connect: ", ibm_db.conn_error())

SUBJECT = "IBM Inventory Management Application"

def sendgridmail(user,TEXT):    
    try:
        print("Helo")
        content = Content("text/plain",TEXT)
        message = Mail(
            from_email=os.environ.get('SENDGRID_FROM_EMAIL'),
            to_emails=user,
            subject=SUBJECT,
            html_content=content)
        print("Hello1")
        sg = sendgrid.SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        print("Hello2")
        response = sg.send(message)
        print("Hello3")
        print(response.status_code)
        print(response.body)
        print(response.headers)

    except Exception as e:
        print("Hello4")
        print(e)


@app.route('/')
def index():
    return render_template('home.html')

#Register Form Class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=1, max=25)])
    email = StringField('Email', [validators.length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

#Register new User
@app.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        email = form.email.data
        username = form.username.data
        password = str(form.password.data)

        sql = "SELECT * FROM users WHERE email=?"
        prep_stmt = ibm_db.prepare(conn, sql)
        ibm_db.bind_param(prep_stmt, 1, email)
        ibm_db.execute(prep_stmt)
        account = ibm_db.fetch_assoc(prep_stmt)
        print(account)
        if account:
            error = "Account already exists! Log in to continue !"
        else:
            insert_sql = "INSERT INTO users (email,username,password) values(?,?,?)"
            prep_stmt = ibm_db.prepare(conn, insert_sql)
            ibm_db.bind_param(prep_stmt, 1, email)
            ibm_db.bind_param(prep_stmt, 2, username)
            ibm_db.bind_param(prep_stmt, 3, password)
            ibm_db.execute(prep_stmt)
            sendgridmail(email, "Registered Successfully! Thank you for registering with us")
            flash(" Registration successful. Log in to continue !")
               
        return redirect(url_for('login'))
    return render_template('register.html', form = form)

#User Login
@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        error = None
        account = None
        username = request.form['username']
        password = request.form['password']
        print(username, password)

        sql = "SELECT * FROM users WHERE username=? AND password=?"
        stmt = ibm_db.prepare(conn, sql)
        ibm_db.bind_param(stmt, 1, username)
        ibm_db.bind_param(stmt, 2, password)
        ibm_db.execute(stmt)
        account = ibm_db.fetch_assoc(stmt)
        print(account)
    if account:
        session['logged_in'] = True
        session['username'] = username
        flash("Logged in successfully","success")
        return redirect(url_for('dashboard'))
    else: 
        error = "Incorrect username / password"
        return render_template('login.html', error=error)


#Check for if user is logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

#Main Dashboard Page
@app.route('/dashboard')
@is_logged_in 
def dashboard():
    sql = "SELECT * FROM stock"
    stmt = ibm_db.exec_immediate(conn, sql)
    dictionary = ibm_db.fetch_assoc(stmt)
    stocks = []
    print(dictionary)
    headings = [*dictionary]
    while dictionary != False:
        stocks.append(dictionary)
        dictionary = ibm_db.fetch_assoc(stmt)
    return render_template('dashboard.html',headings=headings, data=stocks)

#User Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for('login'))

#Update Stock Inventory
@app.route('/inventoryUpdate', methods=['POST'])
@is_logged_in
def inventoryUpdate():
    if request.method == "POST":
        try:
            item = request.form['item']
            field = request.form['input-field']
            value = request.form['input-value']
            print(item, field, value)
            insert_sql = 'UPDATE stock SET ' + field + "= ?" + " WHERE STOCK_NAME=?"
            print(insert_sql)
            pstmt = ibm_db.prepare(conn, insert_sql)
            ibm_db.bind_param(pstmt, 1, value)
            ibm_db.bind_param(pstmt, 2, item)
            ibm_db.execute(pstmt)
            if field == 'PRICE_PER_QUANTITY' or field == 'QUANTITY':
                insert_sql = 'SELECT * FROM stocks WHERE STOCK_NAME= ?'
                pstmt = ibm_db.prepare(conn, insert_sql)
                ibm_db.bind_param(pstmt, 1, item)
                ibm_db.execute(pstmt)
                dictonary = ibm_db.fetch_assoc(pstmt)
                print(dictonary)
                total = dictonary['QUANTITY'] * dictonary['PRICE_PER_QUANTITY']
                insert_sql = 'UPDATE stocks SET TOTAL_PRICE=? WHERE STOCK_NAME=?'
                pstmt = ibm_db.prepare(conn, insert_sql)
                ibm_db.bind_param(pstmt, 1, total)
                ibm_db.bind_param(pstmt, 2, item)
                ibm_db.execute(pstmt)
        except Exception as e:
            msg = e

        finally:
            
            return redirect(url_for('dashboard'))

# Add to Stock Inventory
@app.route('/addstocks', methods=['POST'])
@is_logged_in
def addStocks():
    if request.method == "POST":
        print(request.form['item'])
        try:
            item = request.form['item']
            quantity = request.form['quantity']
            price = request.form['price']
            total = int(price) * int(quantity)
            insert_sql = 'INSERT INTO stock (STOCK_NAME,QUANTITY,PRICE_PER_QUANTITY,TOTAL_PRICE) VALUES (?,?,?,?)'
            pstmt = ibm_db.prepare(conn, insert_sql)
            ibm_db.bind_param(pstmt, 1, item)
            ibm_db.bind_param(pstmt, 2, quantity)
            ibm_db.bind_param(pstmt, 3, price)
            ibm_db.bind_param(pstmt, 4, total)
            ibm_db.execute(pstmt)

        except Exception as e:
            msg = e

        finally:

            return redirect(url_for('dashboard'))

#Delete from Stock Inventory
@app.route('/deletestocks', methods=['POST'])
@is_logged_in
def deleteStocks():
    if request.method == "POST":
        print(request.form['item'])
        try:
            item = request.form['item']
            insert_sql = 'DELETE FROM stock WHERE STOCK_NAME=?'
            pstmt = ibm_db.prepare(conn, insert_sql)
            ibm_db.bind_param(pstmt, 1, item)
            ibm_db.execute(pstmt)
        except Exception as e:
            msg = e

        finally:
            return redirect(url_for('dashboard'))

#Update Username
@app.route('/update-user', methods=['POST', 'GET'])
@is_logged_in
def updateUser():
    if request.method == "POST":
        try:
            email = session['username']
            value = request.form['input-value']
            insert_sql = 'UPDATE users SET username= ? WHERE username=?'
            pstmt = ibm_db.prepare(conn, insert_sql)
            ibm_db.bind_param(pstmt, 1, value)
            ibm_db.bind_param(pstmt, 2, email)
            print(pstmt)
            ibm_db.execute(pstmt)
        except Exception as e:
            print(e)
            msg = e

        finally:
            session['username'] = value
            return redirect(url_for('profile'))

#Update Password
@app.route('/update-password', methods=['POST', 'GET'])
@is_logged_in
def updatePassword():
    if request.method == "POST":
        try:
            email = session['username']
            password = request.form['prev-password']
            curPassword = request.form['cur-password']
            confirmPassword = request.form['confirm-password']
            insert_sql = 'SELECT * FROM  users WHERE username=? AND PASSWORD=?'
            pstmt = ibm_db.prepare(conn, insert_sql)
            ibm_db.bind_param(pstmt, 1, email)
            ibm_db.bind_param(pstmt, 2, password)
            ibm_db.execute(pstmt)
            dictionary = ibm_db.fetch_assoc(pstmt)
            print(dictionary)
            if curPassword == confirmPassword:
                insert_sql = 'UPDATE users SET PASSWORD=? WHERE username=?'
                pstmt = ibm_db.prepare(conn, insert_sql)
                ibm_db.bind_param(pstmt, 1, confirmPassword)
                ibm_db.bind_param(pstmt, 2, email)
                ibm_db.execute(pstmt)
        except Exception as e:
            msg = e
        finally:
           
            return redirect(url_for('profile'))

#Get Orders
@app.route('/orders', methods=['POST', 'GET'])
@is_logged_in
def orders():
    query = "SELECT * FROM orders"
    stmt = ibm_db.exec_immediate(conn, query)
    dictionary = ibm_db.fetch_assoc(stmt)
    orders = []
    headings = [*dictionary]
    while dictionary != False:
        orders.append(dictionary)
        dictionary = ibm_db.fetch_assoc(stmt)
    return render_template("orders.html", headings=headings, data=orders)

#Create new Order
@app.route('/createOrder', methods=['POST'])
@is_logged_in
def createOrder():
    if request.method == "POST":
        try:
            stock_id = request.form['stock_id']
            query = 'SELECT PRICE_PER_QUANTITY FROM stock WHERE SID= ?'
            stmt = ibm_db.prepare(conn, query)
            ibm_db.bind_param(stmt, 1, stock_id)
            ibm_db.execute(stmt)
            dictionary = ibm_db.fetch_assoc(stmt)
            if dictionary:
                quantity = request.form['quantity']
                date = str(datetime.now().year) + "-" + str(
                    datetime.now().month) + "-" + str(datetime.now().day)
                delivery = datetime.now() + timedelta(days=7)
                delivery_date = str(delivery.year) + "-" + str(
                    delivery.month) + "-" + str(delivery.day)
                price = float(quantity) * \
                    float(dictionary['PRICE_PER_QUANTITY'])
                query = 'INSERT INTO orders (STOCK_ID,QUANTITY,ODATE,DELIVERY_DATE,PRICE) VALUES (?,?,?,?,?)'
                pstmt = ibm_db.prepare(conn, query)
                ibm_db.bind_param(pstmt, 1, stock_id)
                ibm_db.bind_param(pstmt, 2, quantity)
                ibm_db.bind_param(pstmt, 3, date)
                ibm_db.bind_param(pstmt, 4, delivery_date)
                ibm_db.bind_param(pstmt, 5, price)
                ibm_db.execute(pstmt)
        except Exception as e:
            print(e)

        finally:
            return redirect(url_for('orders'))

#Update Order
@app.route('/updateOrder', methods=['POST'])
@is_logged_in
def updateOrder():
    if request.method == "POST":
        try:
            item = request.form['item']
            field = request.form['input-field']
            value = request.form['input-value']
            query = 'UPDATE orders SET ' + field + "= ?" + " WHERE OID=?"
            pstmt = ibm_db.prepare(conn, query)
            ibm_db.bind_param(pstmt, 1, value)
            ibm_db.bind_param(pstmt, 2, item)
            ibm_db.execute(pstmt)
        except Exception as e:
            print(e)

        finally:
            return redirect(url_for('orders'))

#Cancel Order
@app.route('/cancelOrder', methods=['POST'])
@is_logged_in
def cancelOrder():
    if request.method == "POST":
        try:
            order_id = request.form['order_id']
            query = 'DELETE FROM orders WHERE OID=?'
            pstmt = ibm_db.prepare(conn, query)
            ibm_db.bind_param(pstmt, 1, order_id)
            ibm_db.execute(pstmt)
        except Exception as e:
            print(e)

        finally:
            return redirect(url_for('orders'))

#Get Suppliers
@app.route('/suppliers', methods=['POST', 'GET'])
@is_logged_in
def suppliers():
    sql = "SELECT * FROM suppliers"
    stmt = ibm_db.exec_immediate(conn, sql)
    dictionary = ibm_db.fetch_assoc(stmt)
    suppliers = []
    orders_assigned = []
    headings = [*dictionary]
    while dictionary != False:
        suppliers.append(dictionary)
        orders_assigned.append(dictionary['ORDER_ID'])
        dictionary = ibm_db.fetch_assoc(stmt)

    sql = "SELECT OID FROM orders"
    stmt = ibm_db.exec_immediate(conn, sql)
    dictionary = ibm_db.fetch_assoc(stmt)
    order_ids = []
    print("dictionary")
    print(dictionary)
    while dictionary != False:
        order_ids.append(dictionary['OID'])
        dictionary = ibm_db.fetch_assoc(stmt)
    unassigned_order_ids=None
    return render_template("suppliers.html", headings=headings, data=suppliers, order_ids=order_ids)

#Update Supplier
@app.route('/updatesupplier', methods=['POST'])
@is_logged_in
def UpdateSupplier():
    if request.method == "POST":
        try:
            item = request.form['name']
            field = request.form['input-field']
            value = request.form['input-value']
            print(item, field, value)
            insert_sql = 'UPDATE suppliers SET ' + field + "= ?" + " WHERE SNAME=?"
            print(insert_sql)
            pstmt = ibm_db.prepare(conn, insert_sql)
            ibm_db.bind_param(pstmt, 1, value)
            ibm_db.bind_param(pstmt, 2, item)
            ibm_db.execute(pstmt)
        except Exception as e:
            msg = e

        finally:
            return redirect(url_for('suppliers'))

# Add new Supplier
@app.route('/addsupplier', methods=['POST'])
@is_logged_in
def addSupplier():
    if request.method == "POST":
        try:
            name = request.form['name']
            order_id = request.form.get('order-id-select')
            print(order_id)
            location = request.form['location']
            insert_sql = 'INSERT INTO suppliers (SNAME,ORDER_ID,SLOCATION) VALUES (?,?,?)'
            pstmt = ibm_db.prepare(conn, insert_sql)
            ibm_db.bind_param(pstmt, 1, name)
            ibm_db.bind_param(pstmt, 2, order_id)
            ibm_db.bind_param(pstmt, 3, location)
            ibm_db.execute(pstmt)

        except Exception as e:
            msg = e

        finally:
            return redirect(url_for('suppliers'))

#Delete Supplier
@app.route('/deletesupplier', methods=['POST'])
@is_logged_in
def deleteSupplier():
    if request.method == "POST":
        try:
            item = request.form['name']
            insert_sql = 'DELETE FROM suppliers WHERE SNAME=?'
            pstmt = ibm_db.prepare(conn, insert_sql)
            ibm_db.bind_param(pstmt, 1, item)
            ibm_db.execute(pstmt)
        except Exception as e:
            msg = e

        finally:
            return redirect(url_for('suppliers'))

#Get User's Profile
@app.route('/profile', methods=['POST', 'GET'])
@is_logged_in
def profile():
    if request.method == "GET":
     
            email = session['username']
            insert_sql = 'SELECT * FROM users WHERE username=?'
            pstmt = ibm_db.prepare(conn, insert_sql)
            ibm_db.bind_param(pstmt, 1, email)
            ibm_db.execute(pstmt)
            dictionary = ibm_db.fetch_assoc(pstmt)
            print(dictionary)
            return render_template("profile.html", data=dictionary)

if __name__ == '__main__':
    
    app.run(host="0.0.0.0",port=5000)