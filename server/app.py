from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from sqlalchemy import create_engine, URL
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
    print(f"DEBUG - Database URL from env: {os.getenv('DATABASE_URL', 'NOT SET')}")
    print(f"DEBUG - Database URL from config: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # **FORÇAR CONEXÃO SUPABASE SEMPRE EM PRODUÇÃO**
    if env == 'production':
        print("DEBUG: Produção detectada - configurando Supabase manualmente...")
        
        # Configuração MANUAL do Supabase
        connection_url = URL.create(
            drivername="postgresql+psycopg",
            username="postgres.kwuxogvfhfgryiquhshl",  # USUÁRIO COM PROJECT-REF
            password="Itc3dku5uVIAXFgC",  # SENHA
            host="aws-1-sa-east-1.pooler.supabase.com",
            port=5432,
            database="postgres",
            query={
                "sslmode": "require",
                "connect_timeout": "10",
                "keepalives_idle": "30",
                "keepalives_interval": "10",
                "keepalives_count": "5"
            }
        )
        
        # Cria engine manualmente
        engine = create_engine(
            connection_url,
            pool_pre_ping=True,
            echo=False,
            pool_size=5,
            max_overflow=10
        )
        
        # Configura o SQLAlchemy
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
        }
        
        # Sobrescreve a URL no config
        app.config['SQLALCHEMY_DATABASE_URI'] = str(connection_url)
        
        print(f"DEBUG: Supabase URL configurada: {str(connection_url).replace('Itc3dku5uVIAXFgC', '***')}")
    
    # Inicializa o SQLAlchemy
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
