from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User
import sentiment_service as ss
import io


def create_app():
    # Using the app factory pattern (common in Flask) so the app can be created
    # in a clean way for scripts/tests later. As a beginner, this also helps
    # avoid "everything in global scope" problems.
    app = Flask(__name__)

    # Hard-coded config for local development.
    # (In production you'd move SECRET_KEY and DB URI to environment variables.)
    app.config["SECRET_KEY"] = "dev-change-me"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize SQLAlchemy with the Flask app
    db.init_app(app)

    # Basic Flask-Login setup for session-based auth.
    # Keeping it minimal: login_required + current_user is enough for this project.
    login_manager = LoginManager()
    login_manager.login_view = "login"  # where unauthorized users are redirected
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        # Flask-Login stores user_id in the session; we load the User from the DB.
        # Using db.session.get is a simple modern way to query by primary key.
        return db.session.get(User, int(user_id))

    # Auto-create tables on startup.
    # This is convenient for small demos, but a real project would use migrations
    # (e.g., Flask-Migrate / Alembic) instead of create_all().
    with app.app_context():
        db.create_all()

    @app.route("/")
    def home():
        # A simple "router" landing page:
        # - logged in -> dashboard
        # - otherwise -> login
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        # Standard form-based registration.
        # Using flash() so templates can show user-friendly messages.
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()

            # Beginner-friendly input validation (simple but clear).
            if not username or not password:
                flash("Username and password required.")
                return redirect(url_for("register"))

            # Prevent duplicate usernames.
            if User.query.filter_by(username=username).first():
                flash("Username already exists.")
                return redirect(url_for("register"))

            # Create user record and store hashed password via User model helper.
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            flash("Registration successful. Please log in.")
            return redirect(url_for("login"))

        # GET request: show registration page
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        # Basic login flow:
        # - lookup user
        # - verify password
        # - establish session with login_user()
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()

            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for("dashboard"))

            # Generic error message on purpose (doesn't reveal which field was wrong).
            flash("Invalid username or password.")
            return redirect(url_for("login"))

        # GET request: show login page
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        # End the user session and send them back to login page.
        logout_user()
        return redirect(url_for("login"))

    @app.route("/download/<mode>")
    @login_required
    def download_csv(mode):
        # Allow downloading the raw data as CSV.
        # mode is part of the route, so we sanitize it to only allow valid values.
        mode = (mode or "positive").lower()
        if mode not in ("positive", "negative"):
            mode = "positive"

        # Pull DataFrames from the sentiment service.
        # debug=True is intentionally used during development to surface errors/logs.
        # (Later we would likely wire this to app.config or an env variable.)
        top_df, low_df = ss.build_treemap_data(debug=True)
        df = top_df if mode == "positive" else low_df

        # Build an in-memory CSV so we don't have to write temporary files.
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)

        # Flask send_file expects bytes for a binary stream, so we encode the string CSV.
        return send_file(
            io.BytesIO(buffer.getvalue().encode("utf-8")),
            mimetype="text/csv; charset=utf-8",
            as_attachment=True,
            download_name=f"sp500_sentiment_{mode}.csv"
        )

    @app.route("/dashboard")
    @login_required
    def dashboard():
        # Dashboard itself is mostly frontend logic; backend only renders the template.
        return render_template("dashboard.html")

    @app.route("/api/treemap")
    @login_required
    def api_treemap():
        # JSON API endpoint that the frontend can call to get plot data.
        # Query param: ?mode=positive|negative
        mode = request.args.get("mode", "positive").lower()
        if mode not in ("positive", "negative"):
            mode = "positive"

        # The service layer handles caching + building Plotly-compatible dict JSON.
        fig_dict = ss.build_treemap_json(mode=mode, debug=True)
        return jsonify(fig_dict)

    return app


if __name__ == "__main__":
    # Run a local dev server.
    # debug=True enables auto-reload + better error pages (not for production).
    app = create_app()
    app.run(debug=True)