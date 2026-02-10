from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# SQLAlchemy instance is created here and initialized later in the app factory.
# This keeps the model definition decoupled from the Flask app creation.
db = SQLAlchemy()


class User(UserMixin, db.Model):
    # Single-table user model for authentication.
    # Intentionally minimal: only fields required for login/session handling.

    # Primary key required by both SQLAlchemy and Flask-Login.
    id = db.Column(db.Integer, primary_key=True)

    # Username is unique and required.
    # Length is conservative to keep things simple.
    username = db.Column(db.String(80), unique=True, nullable=False)

    # Storing a password hash instead of the raw password.
    # The column is sized generously to accommodate different hash formats.
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, raw_password: str) -> None:
        """
        Hash and store the user's password.

        This helper exists to keep password logic out of route handlers,
        even though the overall auth system is intentionally simple.
        """
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """
        Verify a raw password against the stored hash.

        Returning a boolean keeps the calling code very straightforward,
        which is helpful while learning Flask-Login flows.
        """
        return check_password_hash(self.password_hash, raw_password)