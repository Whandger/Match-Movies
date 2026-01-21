import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def run_sql_script():
    load_dotenv()
    
    # Usa DATABASE_URL se disponível, senão constrói a partir das variáveis
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        # Constrói a URL do PostgreSQL
        host = os.getenv('MYSQL_HOST', 'localhost')
        user = os.getenv('MYSQL_USER', 'postgres')
        password = os.getenv('MYSQL_PASSWORD', '')
        port = os.getenv('MYSQL_PORT', '5432')
        database = os.getenv('MYSQL_DB', 'postgres')
        
        database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    try:
        # Cria engine do SQLAlchemy
        engine = create_engine(database_url)
        
        # Script SQL para PostgreSQL (já criamos no Supabase!)
        sql_script = """
        -- 1. Tabela de Usuários (PostgreSQL)
        CREATE TABLE IF NOT EXISTS MoviesUsers (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );

        -- 2. Tabela de Reações
        CREATE TABLE IF NOT EXISTS MoviesReacted (
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL,
            movie_id VARCHAR(20) NOT NULL,
            action VARCHAR(20) NOT NULL CHECK (action IN ('like', 'dislike', 'indicate')),
            reacted_at TIMESTAMP DEFAULT NOW(),
            UNIQUE (user_id, movie_id),
            FOREIGN KEY (user_id) REFERENCES MoviesUsers(id) ON DELETE CASCADE
        );

        -- 3. Tabela de Conexões e Matches
        CREATE TABLE IF NOT EXISTS UserConnections (
            id SERIAL PRIMARY KEY,
            user1_id INT NOT NULL,
            user2_id INT NOT NULL,
            connected_at TIMESTAMP DEFAULT NOW(),
            is_active BOOLEAN DEFAULT TRUE,
            match_count INT DEFAULT 0,
            last_match_at TIMESTAMP NULL,
            matched_movies JSONB DEFAULT '[]'::jsonb,
            pending_indications JSONB DEFAULT '[]'::jsonb,
            FOREIGN KEY (user1_id) REFERENCES MoviesUsers(id) ON DELETE CASCADE,
            FOREIGN KEY (user2_id) REFERENCES MoviesUsers(id) ON DELETE CASCADE,
            UNIQUE (user1_id, user2_id)
        );
        """
        
        # Executa o script
        with engine.connect() as connection:
            # Divide e executa os comandos
            for statement in sql_script.split(';'):
                stmt = statement.strip()
                if stmt:
                    connection.execute(text(stmt))
            connection.commit()
        
        print('✅ Banco de dados PostgreSQL inicializado com sucesso.')
        
    except Exception as e:
        print('❌ Erro ao inicializar o banco de dados PostgreSQL:', e)