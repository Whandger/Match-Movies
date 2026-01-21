from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

# Instância global do SQLAlchemy
db = SQLAlchemy()

def create_app():
    print("Criando app e registrando blueprints...")

    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), '..', 'template'),
        static_folder=os.path.join(os.path.dirname(__file__), '..', 'static')
    )

    # Verifica o ambiente (development ou production)
    env = os.getenv('FLASK_ENV', 'production')

    # Configurações de produção ou desenvolvimento
    if env == 'production':
        from server.config.config import ProductionConfig
        app.config.from_object(ProductionConfig)
    else:
        from server.config.config import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)

    # Configura a chave secreta
    app.secret_key = os.getenv('SECRET_KEY', 'uma_chave_secreta_segura')

    # Inicializa o SQLAlchemy com a app
    db.init_app(app)
    app.extensions['db'] = db

    # Registrar blueprints
    print(app.url_map)
    if 'page' not in app.blueprints:
        from server.routes.routes import page_bp
        app.register_blueprint(page_bp)
        print(app.url_map)

    if 'login' not in app.blueprints:
        from server.routes.loginroutes import login_bp
        app.register_blueprint(login_bp)

    if 'movies' not in app.blueprints:
        from server.routes.movies import movies_bp
        app.register_blueprint(movies_bp, url_prefix='/api/movies')
        print("Blueprint 'movies' registrado")

    return app


if __name__ == '__main__':
    app = create_app()
    debug_mode = os.getenv('FLASK_ENV', 'production') != 'production'
    app.run(debug=debug_mode, use_reloader=False)
