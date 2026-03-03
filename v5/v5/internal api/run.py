from disaster_api import create_app
from dotenv import load_dotenv


load_dotenv()
app = create_app()


if __name__ == "__main__":
    settings = app.config["SETTINGS"]
    app.run(
        host=settings.flask_host,
        port=settings.flask_port,
        debug=settings.flask_debug,
    )
