from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
import os

# Instância global do SQLAlchemy
db = SQLAlchemy()

def create_app():
    print("Criando app e registrando blueprints...")

    # Cria a aplicação Flask
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), '..', 'template'),
        static_folder=os.path.join(os.path.dirname(__file__), '..', 'static')
    )

    # Configura ambiente: production ou development
    env = os.getenv('FLASK_ENV', 'development')

    if env == 'production':
        from server.config.config import ProductionConfig
        app.config.from_object(ProductionConfig)
    else:
        from server.config.config import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)

    # Chave secreta para sessões
    app.secret_key = os.getenv('SECRET_KEY', 'sua_chave_secreta_segura')

    # Configura o SQLAlchemy com a URL do Supabase
    db_user = os.getenv('DB_USER')        # Ex: postgres
    db_pass = os.getenv('DB_PASSWORD')    # Ex: yYJDEM5ENvCMti3q
    db_host = os.getenv('DB_HOST')        # Ex: db.kwuxogvfhfgryiquhshl.supabase.co
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'postgres')

    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"postgresql+psycopg://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?sslmode=require"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inicializa SQLAlchemy
    db.init_app(app)
    app.extensions['db'] = db

    # Registrar blueprints
    if 'page' not in app.blueprints:
        from server.routes.routes import page_bp
        app.register_blueprint(page_bp)
        print("Blueprint 'page' registrado")

    if 'login' not in app.blueprints:
        from server.routes.loginroutes import login_bp
        app.register_blueprint(login_bp)
        print("Blueprint 'login' registrado")

    if 'movies' not in app.blueprints:
        from server.routes.movies import movies_bp
        app.register_blueprint(movies_bp, url_prefix='/api/movies')
        print("Blueprint 'movies' registrado")

    print(app.url_map)
    return app

if __name__ == '__main__':
    app = create_app()
    debug_mode = os.getenv('FLASK_ENV', 'development') == 'development'
    app.run(debug=debug_mode, use_reloader=False)
