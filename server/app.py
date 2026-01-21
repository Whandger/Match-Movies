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
    print(f"DEBUG - Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # **SOLUÇÃO: Criar engine manualmente para Supabase**
    db_url = app.config['SQLALCHEMY_DATABASE_URI']
    
    if 'supabase' in db_url or 'pooler.supabase.com' in db_url:
        print("DEBUG: Usando configuração manual para Supabase...")
        
        # Cria URL de conexão com todos os parâmetros corretos
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
            echo=False  # Mude para True para ver queries SQL no log
        )
        
        # Configura o SQLAlchemy com o engine manual
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
        }
        
        # Inicializa o SQLAlchemy
        db.init_app(app)
        
        # Sobrescreve o engine com o nosso engine configurado corretamente
        with app.app_context():
            db.engine = engine
            # Atualiza a sessão para usar o novo engine
            db.session.remove()
            db.session = db.create_scoped_session(options={'bind': engine})
            
        print("DEBUG: Engine Supabase configurado manualmente")
    else:
        # Para SQLite ou outras conexões, usa configuração normal
        db.init_app(app)
        print("DEBUG: Usando configuração padrão do SQLAlchemy")
    
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
