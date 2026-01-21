from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from sqlalchemy import create_engine, text
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

    print(f"DEBUG: Ambiente: {env}")
    
    # **CONEXÃO SUPABASE EM PRODUÇÃO - TESTE MULTIPLAS URLs**
    if env == 'production':
        print("DEBUG: Configurando Supabase...")
        
        password = "Bh54YB7vBK5RvChG"  # SENHA NOVA DO SUPABASE
        
        # LISTA DE URLs PARA TESTAR (em ordem de probabilidade)
        test_urls = [
            # 1. URL EXATA do Supabase Session Pooler (mais provável)
            f"postgresql://postgres.kwuxogvfhfgryiquhshl:{password}@aws-1-sa-east-1.pooler.supabase.com:5432/postgres?sslmode=require&connect_timeout=10",
            
            # 2. Com psycopg3 driver
            f"postgresql+psycopg://postgres.kwuxogvfhfgryiquhshl:{password}@aws-1-sa-east-1.pooler.supabase.com:5432/postgres?sslmode=require&connect_timeout=10",
            
            # 3. Usuário escapado
            f"postgresql+psycopg://postgres%2Ekwuxogvfhfgryiquhshl:{password}@aws-1-sa-east-1.pooler.supabase.com:5432/postgres?sslmode=require&connect_timeout=10",
            
            # 4. Transaction Pooler (porta 6543)
            f"postgresql+psycopg://postgres.kwuxogvfhfgryiquhshl:{password}@aws-0-sa-east-1.pooler.supabase.com:6543/postgres?sslmode=require&connect_timeout=10",
            
            # 5. Conexão direta (talvez com IPv4 add-on?)
            f"postgresql+psycopg://postgres:{password}@db.kwuxogvfhfgryiquhshl.supabase.co:5432/postgres?sslmode=require&connect_timeout=10",
        ]
        
        success = False
        chosen_url = ""
        
        # Testa cada URL
        for i, connection_string in enumerate(test_urls, 1):
            print(f"\nDEBUG: Testando URL {i}/5...")
            safe_string = connection_string.replace(password, "***")
            print(f"URL: {safe_string}")
            
            try:
                engine = create_engine(
                    connection_string,
                    pool_pre_ping=True,
                    echo=False,
                    connect_args={"connect_timeout": 5}
                )
                
                # Tenta conectar
                with engine.connect() as conn:
                    # Tenta uma query simples
                    result = conn.execute(text("SELECT 1"))
                    if result.scalar() == 1:
                        print(f"✅ CONEXÃO {i} BEM-SUCEDIDA!")
                        app.config['SQLALCHEMY_DATABASE_URI'] = connection_string
                        chosen_url = safe_string
                        success = True
                        
                        # Cria as tabelas se não existirem
                        try:
                            print("DEBUG: Verificando tabelas...")
                            # Aqui você pode adicionar db.create_all() se necessário
                        except Exception as e:
                            print(f"DEBUG: Nota sobre tabelas: {str(e)[:100]}")
                        
                        break
                        
            except Exception as e:
                error_msg = str(e)
                print(f"❌ Conexão {i} falhou: {error_msg[:150]}")
                continue
        
        if not success:
            print("\n⚠️ TODAS as conexões falharam. Usando SQLite como fallback.")
            print("DEBUG: Considere ativar IPv4 add-on no Supabase (US$4/mês)")
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///matchmovies.db'
        else:
            print(f"\n🎉 Conexão estabelecida com: {chosen_url}")
    
    print(f"DEBUG: URL final: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Não definida').replace(password, '***') if 'password' in locals() else app.config.get('SQLALCHEMY_DATABASE_URI', 'Não definida')}")
    
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
