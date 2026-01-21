from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from server.config.config import ProductionConfig, DevelopmentConfig

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
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(DevelopmentConfig)

    # LOG TEMPORÁRIO para debug
    print(f"DEBUG - Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # Inicializa o SQLAlchemy com a app
    db.init_app(app)
    app.extensions['db'] = db

    # Registrar blueprints
    print(app.url_map)
    from server.routes.routes import page_bp
    from server.routes.loginroutes import login_bp
    from server.routes.movies import movies_bp

    if 'page' not in app.blueprints:
        app.register_blueprint(page_bp)

    if 'login' not in app.blueprints:
        app.register_blueprint(login_bp)

    if 'movies' not in app.blueprints:
        app.register_blueprint(movies_bp, url_prefix='/api/movies')
        print("Blueprint 'movies' registrado")

    return app

if __name__ == '__main__':
    app = create_app()
    debug_mode = os.getenv('FLASK_ENV', 'production') != 'production'
    app.run(debug=debug_mode, use_reloader=False)
