from flask import Flask, redirect, make_response, render_template, request, session
from cs50 import SQL
from flask_session.__init__ import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import calculate_score, password_check, plot_data
import os
import json
import psycopg2

app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///database.db")

# PostgreSQL
DATABASE_URL = os.environ['DATABASE_URL']

def db_execute(query, values=None):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    if values:
        cur.execute(query, values)
        print(query, values)
    else:
        cur.execute(query)
        print(query)      

    if query.startswith("SELECT"):
        result = cur.fetchall()
        cur.close()
        conn.close()
        return result
    else:
        conn.commit()
        cur.close()
        conn.close()
        return


# Provide Nav Links for all pages
@app.context_processor
def inject_menu():

    # Fill in with your actual menu dictionary:
    menu = db_execute("SELECT comp, name FROM comps;")
    print(menu)

    return dict(menu=menu)


@app.route("/")
def home():
    
    return render_template("home.html")


@app.route("/comp/<comp_id>", methods=['POST', 'GET'])
def comp(comp_id):
    # SQLite
    #info = db.execute("SELECT * FROM comps WHERE comp = ?", comp_id)[0]
    #comp = comp_id
    #no_climbs = info["climbs"]
    #zone = info["zone"]
    #top = info["top"]

    # PostgreSQL
    info = db_execute("SELECT * FROM comps WHERE comp = %s;", (comp_id,))[0]
    comp = comp_id
    no_climbs = info[3]
    zone = info[4]
    top = info[5]


    if request.method == 'POST':
            climb_data = []

            for n in range(1,no_climbs+1):
                climb_data.append(request.form.get(f'climb-{n}'))

            # If User is logged in
            if session:
                #print("Logged in.")

                # If User already has a saved list of results - SQLite
                #if db.execute("SELECT * FROM results WHERE user_id = ? AND comp = ?", session["user_id"], comp):
                #    db.execute("UPDATE results SET results = ? WHERE user_id = ? AND comp = ?", json.dumps(climb_data), session["user_id"],comp)
                #else:
                #    db.execute("INSERT INTO results (user_id, comp, results) VALUES(?, ?, ?)", session["user_id"], comp, json.dumps(climb_data))
                #results = json.loads(db.execute("SELECT results FROM results WHERE user_id = ? AND comp = ?", session["user_id"], comp)[0]["results"])

                # If User already has a saved list of results - PostgreSQL
                logged_in = db_execute("SELECT * FROM results WHERE user_id = %s AND comp = %s;", (session["user_id"], comp))
                if logged_in:
                    db_execute("UPDATE results SET results = %s WHERE user_id = %s AND comp = %s", (json.dumps(climb_data), session["user_id"],comp))
                else:
                    db_execute("INSERT INTO results (user_id, comp, results) VALUES(%s, %s, %s)", (session["user_id"], comp, json.dumps(climb_data)))

                json_results = db_execute("SELECT results FROM results WHERE user_id = %s AND comp = %s", (session["user_id"], comp))
                print(json_results)
                results = json.loads(json_results[0][0])


            else:
                results = climb_data

            # Calculate score
            score = calculate_score(climb_data,zone,top)

    else:

        # Get data from cookies
        score = request.cookies.get(f'{comp}_score')
        print(score)
        if score is None:
            score = 0
        else:
            score = int(score)

        if session:
            #data = db.execute("SELECT * FROM results WHERE user_id = ? AND comp = ?", session["user_id"], comp)
            data = db_execute("SELECT * FROM  results WHERE user_id = %s AND comp = %s;", (session["user_id"], comp))
            if data:
                results = json.loads(data[0][3])
                #results = json.loads(data[0]["results"])
                score = calculate_score(results,zone,top)
            else:
                results = []
        elif f'{comp}_data' in request.cookies:
            results = json.loads(request.cookies.get(f'{comp}_data'))
        else:
            results = []

        #return render_template("comp.html", comp=comp, no_climbs=no_climbs, score=score, results=results, figure=figure)

    # Create figure, using data from cookies
    if not isinstance(score, int):
        score = 0

    figure = plot_data(comp_id, score)

    resp = make_response(render_template('comp.html', comp=comp, no_climbs=no_climbs, score=score, results=results, figure=figure))

    # Set cookies
    resp.set_cookie(f'{comp}_score', str(score))
    resp.set_cookie(f'{comp}_data', json.dumps(results))
            
    return resp


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")

    else:
        username = request.form.get("username")
        password = request.form.get("password")

        res = password_check(password)
        print(res)

        if not res['password_ok']:
            return render_template("register.html", error="Passwords do not meet specified requirements.")

        confirmation = request.form.get("confirmation")

        if not username:
            return render_template("register.html", error="No username provided.")

        if not password:
            return render_template("register.html", error="No password provided.")

        if password != confirmation:
            return render_template("register.html", error="Password do not match.")

        #other_users = db.execute("SELECT * FROM users WHERE username = ?", username)
        other_users = db_execute("SELECT * FROM users WHERE username = %s;", (username,))

        if other_users:
            return render_template("register.html", error="Username already in use.")

        #db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, generate_password_hash(password))
        db_execute("INSERT INTO users (username, hash) VALUES(%s, %s);", (username, generate_password_hash(password)))
        return render_template("login.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("login.html", error="No username provided.")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("login.html", error="No password provided.")

        # Query database for username
        #rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        rows = db_execute("SELECT * FROM users WHERE username = %s;", (request.form.get("username"),))

        # Ensure username exists and password is correct
        #if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
        if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
            return render_template("login.html", error="Invalid username and/or password.")

        # Remember which user has logged in
        #session["user_id"] = rows[0]["id"]
        #session["username"] = rows[0]["username"]
        session["user_id"] = rows[0][0]
        session["username"] = rows[0][1]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


if __name__ == "__main__":
  app.run()