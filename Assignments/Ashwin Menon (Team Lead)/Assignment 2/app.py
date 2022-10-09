from email import message
from flask import Flask, render_template, request
import ibm_db

app = Flask(__name__)

dsn_hostname = "ba99a9e6-d59e-4883-8fc0-d6a8c9f7a08f.c1ogj3sd0tgtu0lqde00.databases.appdomain.cloud" 
dsn_uid = "wpm42097"        
dsn_pwd = "49qAzk08vjYmpRLb"      

dsn_driver = "{IBM DB2 ODBC DRIVER}"
dsn_database = "bludb"            
dsn_port = "31321"                
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
    print("Hi")
    conn = ibm_db.connect(dsn, "", "")
    print ("Connected to database: ", dsn_database, "as user: ", dsn_uid, "on host: ", dsn_hostname)

    stmt = ibm_db.exec_immediate(conn, "SELECT * FROM USER")
    result = ibm_db.fetch_both(stmt)
    while( result ):
        print ("Result from XMLSerialize and XMLQuery:", result)
        result = ibm_db.fetch_both(stmt)

except:
    print ("Unable to connect: ", ibm_db.conn_errormsg() )

@app.route("/")
def homepage():
    return render_template("reg.html")

@app.route("/", methods=['POST'])
def addUser():
    user = request.form['uname']
    pwd = request.form['pass']
    email = request.form['email']
    rno = request.form['roll']

    stmt = ibm_db.exec_immediate(conn, "INSERT INTO USER VALUES('" + user + "', '" + pwd + "', '" + email + "', '" + rno + "')")
    result=ibm_db.num_rows(stmt)

    print(result)

    if(result == 1):
        return render_template("reg.html", message="User added successfully!")
    else:
        return render_template("reg.html", message="\n")

@app.route("/login")
def render_login(accountok=True):
    if(accountok==True):
        return render_template("login.html", message="")
    else:
        return render_template("login.html", message="Username / Password is incorrect")

@app.route("/login", methods=['POST'])
def checkLogin():
    user = request.form['uname']
    pwd = request.form['pass']

    stmt = ibm_db.exec_immediate(conn, "SELECT * FROM USER WHERE USERNAME = '" + user + "' AND PASSWORD = '" + pwd + "'")
    result = ibm_db.fetch_both(stmt)

    print(result)

    if(result):
        return render_welcome(result[0], result[1], result[2], result[3])
    else:
        return render_login(False)

@app.route("/welcome")
def render_welcome(uname, pwd, email,rno):
    return render_template("welcome.html", user=uname, email=email, rno=rno, pwd=pwd)

if __name__=="__main__":
    app.run(debug=True, host='localhost')