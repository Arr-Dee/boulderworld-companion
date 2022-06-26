import re
from traceback import print_tb
from flask import Flask, redirect, make_response, render_template, request, session, url_for
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

# SQLite
#db = SQL("sqlite:///database.db")

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


# Provides Nav Links for all pages
@app.context_processor
def inject_menu():

    # Fill in with your actual menu dictionary:
    menu = db_execute("SELECT comp, name FROM comps;")
    # print(menu)

    return dict(menu=menu)


# HOME
@app.route("/")
def home():
    info  = db_execute("SELECT * FROM comps ORDER by id DESC LIMIT 1")
    return render_template("home.html", info=info)


# COMPETITION PAGES
@app.route("/comp/<comp_id>", methods=['POST', 'GET'])
def comp(comp_id):
    # SQLite
    #info = db.execute("SELECT * FROM comps WHERE comp = ?", comp_id)[0]
    #comp = comp_id
    #no_climbs = info["climbs"]
    #zone = info["zone"]
    #top = info["top"]

    session['url'] = url_for('comp', comp_id=comp_id)
    print(session['url'])

    # PostgreSQL
    info = db_execute("SELECT * FROM comps WHERE comp = %s;", (comp_id,))[0]
    comp = comp_id
    name = info[2]
    no_climbs = info[3]
    zone = info[4]
    top = info[5]

    if request.method == 'POST':
            climb_data = [request.form.get(f'climb-{n}') for n in range(1,no_climbs+1)]

            # If User is logged in
            try:
                session["user_id"]
                # If User already has a saved list of results - PostgreSQL
                logged_in = db_execute("SELECT * FROM results WHERE user_id = %s AND comp = %s;", (session["user_id"], comp))
                if logged_in:
                    db_execute("UPDATE results SET results = %s WHERE user_id = %s AND comp = %s", (json.dumps(climb_data), session["user_id"],comp))
                else:
                    db_execute("INSERT INTO results (user_id, comp, results) VALUES(%s, %s, %s)", (session["user_id"], comp, json.dumps(climb_data)))

                json_results = db_execute("SELECT results FROM results WHERE user_id = %s AND comp = %s", (session["user_id"], comp))
                # print(json_results)
                results = json.loads(json_results[0][0])

            except:
                results = climb_data

            # Calculate score
            score = calculate_score(climb_data,zone,top)

    else:

        # Get data from cookies
        score = request.cookies.get(f'{comp}_score')
        # print(score)

        if score is None:
            score = 0
        else:
            score = int(score)

        try:
            session["user_id"]
            data = db_execute("SELECT * FROM  results WHERE user_id = %s AND comp = %s;", (session["user_id"], comp))
            if data:
                results = json.loads(data[0][3])
                #results = json.loads(data[0]["results"])
                score = calculate_score(results,zone,top)
            else:
                results = []
        except:
            if f'{comp}_data' in request.cookies:
                results = json.loads(request.cookies.get(f'{comp}_data'))
            else:
                results = []

        #return render_template("comp.html", comp=comp, no_climbs=no_climbs, score=score, results=results, figure=figure)

    # Create figure, using data from cookies
    if not isinstance(score, int):
        score = 0

    figure = plot_data(comp_id, score)

    resp = make_response(render_template('comp.html', comp=comp, name=name, no_climbs=no_climbs, score=score, zone=zone, top=top, results=results, figure=figure))

    # Set cookies
    resp.set_cookie(f'{comp}_score', str(score))
    resp.set_cookie(f'{comp}_data', json.dumps(results))
            
    return resp


# LEADERBOARD
@app.route("/leaderboard")
def leaderboard():
    # Find all comps in db
    results = db_execute("SELECT users.username, comps.name, results.results, comps.zone, comps.top FROM results INNER JOIN comps ON results.comp = comps.comp INNER JOIN users ON results.user_id = users.id WHERE users.leaderboard is TRUE ORDER BY comps.id")

    # drop down to select comp
    comps = list(set([i[1] for i in results]))
    print(comps)
    # show scores per user in a table
    table = [[i[0], i[1], calculate_score(json.loads(i[2]),i[3],i[4])] for i in results]

    return render_template("leaderboard.html", table=table, comps=comps)


# PROFILE
@app.route("/profile/<username>", methods=['POST', 'GET'])
def profile(username):
    user = db_execute("SELECT * FROM users WHERE username = %s;", (username,))
    if not user:
        # User not found
        return render_template("profile.html")
    
    if request.method == "GET":
        # Render profile, check box if leaderboard = True in .db
        return render_template("profile.html", username=username, checked=user[0][3])
    
    else:
        add_to_lb = False if request.form.get("leaderboard-check") is None else True
        if session["username"] == username:
            db_execute("UPDATE users SET leaderboard = %s WHERE id = %s", (add_to_lb, session["user_id"]))        
            return render_template("profile.html", username=username, checked=add_to_lb, status="Your profile has been updated.")
        else:
            return render_template("profile.html", username=username, checked=add_to_lb)


# REGISTER, LOGIN & LOGOUT ROUTES
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")

    else:
        username = request.form.get("username")
        password = request.form.get("password")       
        add_to_lb = False if request.form.get("leaderboard-check") is None else True
        

        print(add_to_lb)
        

        res = password_check(password)

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
        db_execute("INSERT INTO users (username, hash, leaderboard) VALUES(%s, %s, %s);", (username, generate_password_hash(password), add_to_lb))
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