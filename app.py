from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash

from nostril import nonsense

app = Flask(__name__)

app.config['SECRET_KEY'] = 'super secret key'

app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.config['TEMPLATES_AUTO_RELOAD'] = True
Session(app)

con = sqlite3.connect("database.db", check_same_thread=False)
db = con.cursor()

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/forward', methods=["GET", "POST"])
def forward():
    if request.method == "POST":
        inquiry = request.form.get('inquiry')
        telephone = request.form.get('telephone')
        session['username'] = telephone
       
        if not nonsense(inquiry):
            
            db.execute('SELECT issue and session FROM inquiry WHERE issue = ? AND session = ?', (inquiry.upper(), session['username']))

            if db.fetchall():
                db.execute('DELETE FROM inquiry WHERE issue = ? AND session = ?', (inquiry.upper(), session['username']))
                flash('You already submit this inquiry.')
                return render_template('apology.html')
                
            db.execute("INSERT INTO inquiry (issue, session) VALUES (?, ?)", (inquiry.upper(), session['username']))
            con.commit()

            db.execute('SELECT issue and session FROM inquiry WHERE issue = ? AND session = ?', (inquiry.upper(), session['username']))
          
            if db.fetchone():
                db.execute('SELECT id FROM inquiry WHERE issue = ? AND session = ?', (inquiry.upper(), session['username']))
                id = db.fetchone()
                db.execute("INSERT INTO users (id, telephone) VALUES (?, ?)", (id[0], session['username']))
                con.commit()
                return render_template('inquiry.html', inquiry=inquiry.upper(), id=id[0], telephone=session['username'])
                
        else:
        
            flash("Your text appears to be unintelligible. Please try again.")
            return render_template('apology.html')
    return redirect('/')


@app.route('/inquiry', methods=["GET", "POST"])
def inquiry():
    if request.method == "POST":
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        info = request.form.get('info')
        not_provided = []
       
        if first_name and last_name and email and info:
            
            db.execute('SELECT id FROM users WHERE telephone = ?', [session['username']])
            list = db.fetchall()
            last_index = len(list) - 1
            
            db.execute('UPDATE users SET firstname = ?, lastname = ?, email = ? WHERE id = ?', (first_name, last_name, email, list[last_index][0]))
            db.execute('UPDATE inquiry SET information = ? WHERE id = ?', (info, list[last_index][0]))
            db.execute('SELECT inquiry.id, inquiry.issue, inquiry.information, inquiry.progression, users.firstname, users.lastname, users.email, users.telephone FROM inquiry FULL OUTER JOIN users ON inquiry.id = users.id WHERE inquiry.id = ?', [list[last_index][0]])
            
            counter = session.get('counter')
            session['counter'] = sum(counter)

            return render_template('track.html', users=track(db.fetchall()), last_index = len(db.fetchall()) - 1)
            
        #if the user does not provide some input
        else:
            #show the missing item
            if not first_name:
                not_provided.append('First Name')
            if not last_name:
                not_provided.append('Last Name')
            if not info:
                not_provided.append('Additional Information')
                
            return render_template('apology.html', lists=not_provided)
    return redirect('/login')

@app.route('/login')
def login():
    if 'username' in session:
        db.execute('SELECT inquiry.id, inquiry.issue, inquiry.information, inquiry.progression, users.firstname, users.lastname, users.email, users.telephone FROM inquiry FULL OUTER JOIN users ON inquiry.id = users.id WHERE inquiry.session = ?', [session['username']])
        return render_template('track.html', users=track(db.fetchall()), last_index = len(db.fetchall()) - 1)
    return render_template('login.html')

@app.route('/login_inquiry', methods=['GET', 'POST'])
def login_inquiry():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        telephone = request.form.get('telephone')

        session['username'] = telephone

        db.execute('SELECT telephone, firstname, lastname FROM users WHERE telephone = ?', [session['username']])
        user = db.fetchone()
        if not user:
            return render_template('apology.html')
        else:
            if user[0] == telephone and user[1] == first_name and user[2] == last_name:
                db.execute('SELECT inquiry.id, inquiry.issue, inquiry.information, inquiry.progression, users.firstname, users.lastname, users.email, users.telephone FROM inquiry FULL OUTER JOIN users ON inquiry.id = users.id WHERE users.firstname = ? AND users.lastname = ? AND users.telephone = ?', (first_name, last_name, telephone))
                return render_template('track.html', users=track(db.fetchall()), last_index = len(db.fetchall()) - 1)
    return render_template('login.html')

@app.route('/admin')
def admin():
    define()
    return render_template('admin_login.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin_username = request.form.get('admin_username')
        admin_password = request.form.get('admin_password')

        db.execute("SELECT username, password FROM admin WHERE username = ?", [admin_username])
        admin = db.fetchone()

        if admin[0] == admin_username and check_password_hash(admin[1], admin_password):
            return redirect('/new_assignment')
        else:
            return render_template('apology.html')

    return render_template('admin_login.html')

@app.route('/new_assignment')
def new_assignment():
    db.execute('SELECT inquiry.id, inquiry.issue, inquiry.information, inquiry.progression, users.firstname, users.lastname, users.email, users.telephone FROM inquiry FULL OUTER JOIN users ON inquiry.id = users.id ORDER BY inquiry.id DESC')
    users = db.fetchall()
    new_users = users[0:session.get('counter')]
    return render_template('admin_homepage.html', new_inquiry=session.get('counter'), users=track(new_users))

@app.route('/inquiry_management')
def inquiry_management():
    db.execute('UPDATE inquiry SET progression = "This inquiry is now with us" WHERE progression IS NULL')
    con.commit()
    db.execute('SELECT inquiry.id, inquiry.issue, inquiry.information, inquiry.progression, users.firstname, users.lastname, users.email, users.telephone FROM inquiry FULL OUTER JOIN users ON inquiry.id = users.id ORDER BY inquiry.id DESC')
    users = db.fetchall()
    db.execute('SELECT * FROM progression')
    all_progression = db.fetchall()
    return render_template('inquiry_management.html', users=track(users), options=track_progression(all_progression))

@app.route('/update_progression')
def update_progression():
    id = request.args.get('sid')
    option = request.args.get('s-option')
    db.execute('UPDATE inquiry SET progression = ? WHERE id = ?', (option, int(id)))
    con.commit()
    return redirect('/inquiry_management')

@app.route('/new_progression', methods=["GET", "POST"])
def new_progression():
    if request.method == "POST":
        new_progression = request.form.get('new_progression')
        if not nonsense(new_progression):
            db.execute("INSERT INTO progression (progression) VALUES (?)", [new_progression])
            con.commit()
        else:
            flash("Your text appears to be unintelligible. Please try again.")
            return render_template('apology.html')
    return redirect('/inquiry_management')

@app.route('/to_be_edited_progression')
def to_be_edited_progression():
    selected_progression = request.args.get('s-option')
    db.execute('UPDATE progression SET edit_progression = ? WHERE progression = ?', ('To be edited', selected_progression))
    con.commit()
    db.execute('SELECT id FROM progression WHERE edit_progression = "To be edited"')
    id_edit_progression = db.fetchone()
    return redirect(url_for('edited_progression', id_edit_progression=id_edit_progression[0]))

@app.route('/edited_progression', methods=["GET", "POST"])
def edited_progression():
    if request.method == "POST":
        edited_progression = request.form.get('edited_progression')
        db.execute("SELECT id FROM progression WHERE edit_progression = ?", ['To be edited'])
        id_edit_progression = db.fetchall()

        if len(id_edit_progression) == 1:
            db.execute("UPDATE progression SET progression = ? WHERE id = ?", (edited_progression, id_edit_progression[0][0]))
            con.commit()
            db.execute("UPDATE progression SET edit_progression = NULL WHERE id = ?", [id_edit_progression[0][0]])
            con.commit()
            return redirect('/inquiry_management')
        elif len(id_edit_progression) > 1:
            db.execute("UPDATE progression SET progression = ? WHERE id = ?", (edited_progression, counter))
            con.commit()
            db.execute("UPDATE progression SET edit_progression = NULL WHERE id = ?", [counter])
            con.commit()
            db.execute("UPDATE progression SET edit_progression = NULL WHERE edit_progression = ?", ['To be edited'])
            return redirect('/inquiry_management')

    id_edit_progression = request.args.get('id_edit_progression')
    counter = id_edit_progression
    db.execute('SELECT progression from progression WHERE id = ?', [id_edit_progression])
    to_be_edited_progression = db.fetchone()   
    return render_template('admin_settings.html', to_be_edited_progression=to_be_edited_progression[0])

@app.route('/delete_inquiry')
def delete_inquiry():
    id = request.args.get('sid')
    db.execute('DELETE FROM users WHERE id = ?', [id])
    con.commit()
    db.execute('DELETE FROM inquiry WHERE id = ?', [id])
    con.commit()
    return redirect('/inquiry_management')

@app.route('/general_donation', methods=['GET', 'POST'])
def general_donation():
    if request.method == 'POST':
        option = request.form.get('option')
        amount = request.form.get('amount')
        other_amount = request.form.get('other_amount')
        if amount:
            db.execute('INSERT INTO donation (amount, option, cause) VALUES (?, ?, ?)', (amount, option, 'general'))
            return render_template('donation.html', option=option, amount=amount, other_amount=other_amount)
        else:
            db.execute('INSERT INTO donation (amount, option, cause) VALUES (?, ?, ?)', (other_amount, option, 'general'))
        
    return redirect('/')

@app.route('/donation', methods=['GET', 'POST'])
def donation():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        telephone = request.form.get('telephone')
    

def track(people):
    list = []
    column_name = ['id', 'issue', 'information', 'progression', 'first_name', 'last_name', 'email', 'telephone']
    counter = 0

    for person in people:
        dict = {}

        #if the user exist
        if person:
            #iterate over every element in the 'person' tuple
            for x in range(len(person)):
                if person[x]:
                    dict.setdefault(column_name[x], person[x])
            list.insert(counter, dict)
            counter += 1
    return list 

def track_progression(options):
    list = []
    column_name = ['id', 'option', 'edit_option']
    counter = 0

    for option in options:
        dict = {}
        for x in range(len(option)):
            dict.setdefault(column_name[x], option[x])
        list.insert(counter, dict)
        counter += 1
    return list

def generate_dict(person):
    dict = {}
    column_name = ['id', 'issue', 'information', 'progression', 'first_name', 'last_name', 'email', 'telephone']

    for x in range(len(person)):
        if person[x]:
            dict.setdefault(column_name[x], person[x])

    return dict

def define():
    session['counter'] = 0

def sum(num):
    num += 1
    return num

if __name__ == "__main__":
    app.run(debug=True)