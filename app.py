from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from datetime import date

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ---------- MySQL connection ----------
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='Shreya_2408@',
    database='Flix'
)
cursor = conn.cursor(dictionary=True)

# ---------- Index route redirects to home ----------
@app.route('/')
def index():
    return redirect(url_for('home'))

# ---------- Login ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor.execute("SELECT * FROM USERS WHERE Email=%s AND Password=%s", (email, password))
        user = cursor.fetchone()

        if user:
            session['UserID'] = user['UserID']  # consistent session key
            return redirect(url_for('home'))
        else:
            flash("Invalid email or password")
            return redirect(url_for('login'))
    return render_template('login.html')

# ---------- Signup ----------
@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        fname = request.form['first_name']
        lname = request.form['last_name']
        email = request.form['email']
        pwd = request.form['password']
        try:
            cursor.execute("INSERT INTO USERS (FirstName, LastName, Email, Password) VALUES (%s,%s,%s,%s)",
                           (fname, lname, email, pwd))
            conn.commit()
            flash("Account created! Please login.")
            return redirect(url_for('login'))
        except:
            flash("Email already exists.")
    return render_template('signup.html')

# ---------- Logout ----------
@app.route('/logout')
def logout():
    session.pop('UserID', None)
    return redirect(url_for('login'))

# ---------- Home ----------
@app.route('/home')
def home():
    user_id = session.get('UserID')
    if not user_id:
        return redirect(url_for('login'))

    # All movies and series for the grids
    cursor.execute("SELECT * FROM MOVIE")
    movies = cursor.fetchall()

    cursor.execute("SELECT * FROM SERIES")
    series_list = cursor.fetchall()

    # Try to find a trending movie (most watched in last 7 days)
    cursor.execute("""
        SELECT M.*, COUNT(W.WatchID) AS Views
        FROM WATCH_HISTORY W
        JOIN MOVIE M ON W.MovieID = M.MovieID
        WHERE W.WatchDate >= CURDATE() - INTERVAL 7 DAY
        GROUP BY M.MovieID
        ORDER BY Views DESC
        LIMIT 1
    """)
    trending_movie = cursor.fetchone()

    if trending_movie:
        trending_item = trending_movie
        trending_type = 'movie'
    else:
        # fallback: pick the most recently released series
        cursor.execute("SELECT * FROM SERIES ORDER BY ReleaseDate DESC LIMIT 1")
        trending_series = cursor.fetchone()
        trending_item = trending_series
        trending_type = 'series' if trending_series else None

    return render_template(
        'home.html',
        movies=movies,
        series_list=series_list,
        trending_item=trending_item,
        trending_type=trending_type
    )

# ---------- Movie Details ----------
@app.route('/movie/<int:movie_id>')
def movie_details(movie_id):
    cursor.execute("""
        SELECT M.*, G.GenreName AS Genre
        FROM MOVIE M
        LEFT JOIN GENRE G ON M.GenreID = G.GenreID
        WHERE M.MovieID=%s
    """, (movie_id,))
    movie = cursor.fetchone()

    cursor.execute("""
        SELECT A.Actor_Name 
        FROM ACTOR A
        JOIN MOVIE_ACTOR MA ON A.ActorID=MA.ActorID
        WHERE MA.MovieID=%s
    """, (movie_id,))
    actors = cursor.fetchall()

    cursor.execute("""
        SELECT AVG(RatingValue) as avg_rating 
        FROM RATING 
        WHERE MovieID=%s
    """, (movie_id,))
    avg_rating = cursor.fetchone()['avg_rating'] or 'No ratings'

    return render_template('movie_details.html', movie=movie, actors=actors, avg_rating=avg_rating)
 
# ---------- Series Details ----------
@app.route('/series/<int:series_id>')
def series_details(series_id):
    # Get series info
    cursor.execute("SELECT * FROM SERIES WHERE SeriesID=%s", (series_id,))
    series = cursor.fetchone()

    # Get episodes
    cursor.execute("SELECT * FROM EPISODE WHERE SeriesID=%s ORDER BY SeasonNo, EpisodeNo", (series_id,))
    episodes = cursor.fetchall()

    # Get actors
    cursor.execute("""
        SELECT A.Actor_Name FROM ACTOR A
        JOIN SERIES_ACTOR SA ON A.ActorID=SA.ActorID
        WHERE SA.SeriesID=%s
    """, (series_id,))
    actors = cursor.fetchall()

    # Get average rating from episodes
    cursor.execute("""
        SELECT AVG(RatingValue) as avg_rating
        FROM RATING
        WHERE EpisodeID IN (SELECT EpisodeID FROM EPISODE WHERE SeriesID=%s)
    """, (series_id,))
    avg_rating = cursor.fetchone()['avg_rating']

    return render_template('series_details.html', series=series, episodes=episodes, actors=actors, avg_rating=avg_rating)

# ---------- Profile ----------
@app.route('/profile')
def profile():
    user_id = session.get('UserID')
    if not user_id:
        return redirect(url_for('login'))

    cursor.execute("SELECT * FROM USERS WHERE UserID = %s", (user_id,))
    user = cursor.fetchone()
    cursor.execute("SELECT * FROM PROFILE WHERE UserID = %s", (user_id,))
    profiles = cursor.fetchall()
    return render_template('profile.html', profiles=profiles, user=user)

# ---------- Watch History ----------
@app.route('/watch_history')
def watch_history():
    user_id = session.get('UserID')
    if not user_id:
        return redirect(url_for('login'))

    cursor.execute("""
        SELECT W.WatchDate, W.DurationWatched,
               M.Title AS MovieTitle, M.PosterURL AS MoviePoster,
               S.Title AS SeriesTitle, E.Title AS EpisodeTitle, S.PosterURL AS SeriesPoster
        FROM WATCH_HISTORY W
        JOIN PROFILE P ON W.ProfileID = P.ProfileID
        LEFT JOIN MOVIE M ON W.MovieID = M.MovieID
        LEFT JOIN EPISODE E ON W.EpisodeID = E.EpisodeID
        LEFT JOIN SERIES S ON E.SeriesID = S.SeriesID
        WHERE P.UserID = %s
        ORDER BY W.WatchDate DESC
    """, (user_id,))
    history = cursor.fetchall()
    return render_template('watch_history.html', history=history)

# ---------- Payment ----------
@app.route('/payment')
def payment():
    user_id = session.get('UserID')
    if not user_id:
        return redirect(url_for('login'))

    cursor.execute("""
        SELECT P.*, S.PlanName, P.PaymentMethod
        FROM PAYMENT P
        JOIN SUBSCRIPTION S ON P.SubscriptionID=S.SubscriptionID
        WHERE P.UserID=%s
    """, (user_id,))
    payments = cursor.fetchall()
    return render_template('payment.html', payments=payments)

# ---------- Trending ----------
@app.route('/trending')
def trending():
    user_id = session.get('UserID')
    if not user_id:
        return redirect(url_for('login'))

    cursor.execute("""
        SELECT M.Title, COUNT(W.WatchID) AS Views
        FROM WATCH_HISTORY W
        JOIN MOVIE M ON W.MovieID=M.MovieID
        WHERE W.WatchDate >= CURDATE() - INTERVAL 7 DAY
        GROUP BY M.MovieID
        ORDER BY Views DESC
        LIMIT 10
    """)
    trending = cursor.fetchall()
    return render_template('trending.html', trending=trending)

# ---------- Subscription ----------
@app.route('/subscription')
def subscription():
    user_id = session.get('UserID')
    if not user_id:
        return redirect(url_for('login'))

    cursor.execute("""
        SELECT S.PlanName, S.StartDate, S.EndDate, S.Price, P.PaymentMethod
        FROM SUBSCRIPTION S
        JOIN PAYMENT P ON S.SubscriptionID = P.SubscriptionID
        WHERE P.UserID = %s
        ORDER BY P.PaymentDate DESC
    """, (user_id,))
    subs = cursor.fetchall()
    return render_template('subscription.html', subs=subs)

# ---------- Run App ----------
if __name__ == '__main__':
    app.run(debug=True)