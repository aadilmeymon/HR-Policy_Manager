from flask import Flask

def create_app():
    app = Flask(__name__)

    # Set a secret key for the session
    app.secret_key = b'\xa2\x15\xfe\x03\x97J\x19\x0b\xde\xbe\xfe\x13y\xed\xfb\xbf\x9c\x15\xf0\xd2\x08\xd0'

    from .routes import main
    app.register_blueprint(main)

    return app
