from flask import Blueprint, jsonify, session, request, current_app
from sqlalchemy import text  # ADICIONAR ESTA LINHA
import requests
import random
import os
import json

movies_bp = Blueprint('movies', __name__)

TMDB_API_KEY = '941fae9e612c2f209e18d77a5a760269'

def get_movie_trailer(movie_id):
    """Busca o trailer do filme na API do TMDB"""
    try:
        videos_url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos"
        videos_response = requests.get(
            videos_url,
            params={'api_key': TMDB_API_KEY, 'language': 'pt-BR'},
            timeout=5
        )
        
        if videos_response.status_code == 200:
            videos_data = videos_response.json()
            
            # Procurar por trailers no YouTube
            for video in videos_data.get('results', []):
                if video.get('type') == 'Trailer' and video.get('site') == 'YouTube':
                    youtube_key = video.get('key')
                    if youtube_key:
                        return f"https://www.youtube.com/watch?v={youtube_key}"
            
            # Fallback: qualquer trailer do YouTube
            for video in videos_data.get('results', []):
                if video.get('site') == 'YouTube' and video.get('key'):
                    youtube_key = video.get('key')
                    return f"https://www.youtube.com/watch?v={youtube_key}"
        
        return None  # Nenhum trailer encontrado
        
    except Exception as e:
        print(f"Erro ao buscar trailer: {e}")
        return None

# ============================================================================
# SISTEMA DE MATCHES SIMPLIFICADO (ATUALIZADO)
# ============================================================================

def check_and_create_matches(user_id, movie_id, action):
    """Verifica e cria matches quando dois usuários reagem ao mesmo filme"""
    try:
        # Só verifica matches para likes e indicações
        if action not in ['like', 'indicate']:
            return
        
        db = current_app.extensions.get('db')
        if db is None:
            return
        
        # Buscar conexões ativas do usuário
        connections = db.session.execute(
            text("""
                SELECT 
                    CASE 
                        WHEN user1_id = :user_id THEN user2_id 
                        ELSE user1_id 
                    END as partner_id,
                    id as connection_id
                FROM UserConnections 
                WHERE (user1_id = :user_id OR user2_id = :user_id) AND is_active = TRUE
            """),
            {'user_id': user_id}
        ).fetchall()
        
        for connection in connections:
            partner_id = connection[0]
            connection_id = connection[1]
            
            # Verificar se o parceiro também curtiu/indicou este filme
            partner_reaction = db.session.execute(
                text("""
                    SELECT action FROM MoviesReacted 
                    WHERE user_id = :partner_id AND movie_id = :movie_id 
                    AND action IN ('like', 'indicate')
                """),
                {'partner_id': partner_id, 'movie_id': movie_id}
            ).fetchone()
            
            if partner_reaction:
                # 🎉 MATCH ENCONTRADO! Atualizar a conexão
                update_connection_with_match(db, connection_id, movie_id)
        
        db.session.commit()
        
    except Exception as e:
        print(f"Erro ao verificar matches: {str(e)}")
        db.session.rollback()

def update_connection_with_match(db, connection_id, movie_id):
    """Atualiza a conexão com um novo match usando JSON"""
    try:
        # Buscar matches atuais
        result = db.session.execute(
            text("SELECT matched_movies FROM UserConnections WHERE id = :connection_id"),
            {'connection_id': connection_id}
        ).fetchone()
        
        if result:
            current_matches = result[0] or '[]'
            matches_list = json.loads(current_matches)
            
            # Adicionar novo match se não existir
            if movie_id not in matches_list:
                matches_list.append(movie_id)
                
                # Atualizar a conexão
                db.session.execute(
                    text("""
                        UPDATE UserConnections 
                        SET match_count = match_count + 1,
                            last_match_at = CURRENT_TIMESTAMP,
                            matched_movies = :matched_movies
                        WHERE id = :connection_id
                    """),
                    {
                        'matched_movies': json.dumps(matches_list),
                        'connection_id': connection_id
                    }
                )
                
                print(f"🎉 NOVO MATCH: Conexão {connection_id} - Filme {movie_id}")
                
    except Exception as e:
        print(f"Erro ao atualizar match: {str(e)}")

# ============================================================================
# SISTEMA DE CONEXÃO ENTRE USUÁRIOS (ATUALIZADO)
# ============================================================================

@movies_bp.route('/connect', methods=['POST'])
def connect_users():
    """Conecta dois usuários para compartilhar matches"""
    try:
        print("🎯 CONNECT ROTA CHAMADA - INÍCIO")
        
        # Verificar se usuário está logado
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Usuário não logado'}), 401
        
        current_user_id = session['user_id']
        data = request.get_json()
        target_user_id = data.get('target_user_id')
        
        if not target_user_id:
            return jsonify({'success': False, 'message': 'ID do usuário alvo é obrigatório'}), 400
        
        # CONVERTER PARA INTEIRO
        try:
            target_user_id = int(target_user_id)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'ID do usuário deve ser um número'}), 400
        
        # Verificar se não está tentando conectar consigo mesmo
        if current_user_id == target_user_id:
            return jsonify({'success': False, 'message': 'Não é possível conectar consigo mesmo'}), 400
        
        # Acessar Database (SQLAlchemy)
        db = current_app.extensions.get('db')
        if db is None:
            return jsonify({'success': False, 'message': 'Database não configurado'}), 500
        
        # Verificar se o usuário alvo existe
        target_user = db.session.execute(
            text("SELECT id, username FROM MoviesUsers WHERE id = :target_id"),
            {'target_id': target_user_id}
        ).fetchone()
        
        if not target_user:
            return jsonify({'success': False, 'message': 'Usuário não encontrado'}), 404
        
        # Verificar se já existe conexão entre os usuários
        existing_connection = db.session.execute(
            text("""
                SELECT id FROM UserConnections 
                WHERE (user1_id = :user1 AND user2_id = :user2) 
                   OR (user1_id = :user2 AND user2_id = :user1)
            """),
            {'user1': current_user_id, 'user2': target_user_id}
        ).fetchone()
        
        if existing_connection:
            return jsonify({'success': False, 'message': 'Já existe uma conexão com este usuário'}), 400
        
        # Criar nova conexão COM CAMPOS DE MATCH
        user1_id = min(current_user_id, target_user_id)
        user2_id = max(current_user_id, target_user_id)
        
        db.session.execute(
            text("""
                INSERT INTO UserConnections (user1_id, user2_id, match_count, matched_movies) 
                VALUES (:user1_id, :user2_id, 0, '[]')
            """),
            {'user1_id': user1_id, 'user2_id': user2_id}
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Conexão estabelecida com sucesso!',
            'partner_id': target_user_id
        })
        
    except Exception as e:
        print(f"Erro na conexão: {str(e)}")
        if 'db' in locals():
            db.session.rollback()
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500

@movies_bp.route('/connections')
def get_user_connections():
    """Retorna as conexões ativas do usuário"""
    try:
        if 'user_id' not in session:
            return jsonify({'connections': []})
        
        current_user_id = session['user_id']
        db = current_app.extensions.get('db')
        
        if db is None:
            return jsonify({'connections': []})
        
        connections = db.session.execute(
            text("""
                SELECT 
                    uc.id,
                    CASE 
                        WHEN uc.user1_id = :user_id THEN uc.user2_id 
                        ELSE uc.user1_id 
                    END as partner_id,
                    mu.username as partner_username,
                    uc.connected_at
                FROM UserConnections uc
                JOIN MoviesUsers mu ON mu.id = CASE 
                    WHEN uc.user1_id = :user_id THEN uc.user2_id 
                    ELSE uc.user1_id 
                END
                WHERE (uc.user1_id = :user_id OR uc.user2_id = :user_id) AND uc.is_active = TRUE
            """),
            {'user_id': current_user_id}
        ).fetchall()
        
        connection_list = []
        for conn in connections:
            connection_list.append({
                'connection_id': conn[0],
                'partner_id': conn[1],
                'partner_username': conn[2],
                'connected_at': conn[3].isoformat() if conn[3] else None
            })
        
        return jsonify({'connections': connection_list})
        
    except Exception as e:
        print(f"Erro ao buscar conexões: {str(e)}")
        return jsonify({'connections': []})

# ============================================================================
# ROTA PARA BUSCAR MATCHES
# ============================================================================

@movies_bp.route('/matches')
def get_matches():
    """Retorna todos os matches do usuário logado - VERSÃO SIMPLIFICADA"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não logado'}), 401
        
        user_id = session['user_id']
        db = current_app.extensions.get('db')
        
        if db is None:
            return jsonify({'error': 'Database não configurado'}), 500
        
        # Buscar matches do usuário
        connections_data = db.session.execute(
            text("""
                SELECT 
                    uc.id as connection_id,
                    uc.match_count,
                    uc.last_match_at,
                    uc.matched_movies,
                    CASE 
                        WHEN uc.user1_id = :user_id THEN uc.user2_id 
                        ELSE uc.user1_id 
                    END as partner_id,
                    mu.username as partner_username
                FROM UserConnections uc
                JOIN MoviesUsers mu ON mu.id = CASE 
                    WHEN uc.user1_id = :user_id THEN uc.user2_id 
                    ELSE uc.user1_id 
                END
                WHERE (uc.user1_id = :user_id OR uc.user2_id = :user_id) 
                  AND uc.is_active = TRUE
                  AND uc.match_count > 0
                ORDER BY uc.last_match_at DESC
            """),
            {'user_id': user_id}
        ).fetchall()
        
        # Processar os dados para o frontend
        matches = []
        for row in connections_data:
            matched_movies = json.loads(row[3] or '[]')
            
            for movie_id in matched_movies:
                matches.append({
                    'connection_id': row[0],
                    'total_matches': row[1],
                    'last_match_at': row[2].isoformat() if row[2] else None,
                    'movie_id': movie_id,
                    'partner_id': row[4],
                    'partner_username': row[5]
                })
        
        return jsonify({
            'success': True,
            'matches': matches,
            'total_matches': len(matches)
        })
        
    except Exception as e:
        print(f"Erro ao buscar matches: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# SISTEMA DE FILMES (ATUALIZADO)
# ============================================================================

@movies_bp.route('/random')
def random_movie():
    """Busca um filme aleatório que o usuário ainda não reagiu"""
    try:
        # Verificar se usuário está logado
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não logado'}), 401
        
        user_id = session['user_id']
        
        # Acessar Database
        db = current_app.extensions.get('db')
        if db is None:
            return jsonify({'error': 'Database não configurado'}), 500
        
        # Buscar filmes que o usuário já reagiu
        seen_movies_result = db.session.execute(
            text("SELECT movie_id FROM MoviesReacted WHERE user_id = :user_id"),
            {'user_id': user_id}
        ).fetchall()
        
        seen_movies = [str(row[0]) for row in seen_movies_result]
        
        # Categorias com limites (reduzidos para teste)
        categories = {
            "popular": 700,
            "top_rated": 700, 
            "now_playing": 10,
            "upcoming": 10
        }
        
        # Tentar até 10 vezes buscar um filme válido E não visto
        max_attempts = 10
        
        for attempt in range(max_attempts):
            try:
                chosen_category = random.choice(list(categories.keys()))
                max_page = categories[chosen_category]
                random_page = random.randint(1, max_page)
                
                url = f"https://api.themoviedb.org/3/movie/{chosen_category}?api_key={TMDB_API_KEY}&language=pt-BR&page={random_page}"
                response = requests.get(url, timeout=5)
                
                if response.status_code != 200:
                    continue
                
                data = response.json()
                
                if data.get('results'):
                    # Filtrar filmes válidos E não vistos
                    valid_movies = [
                        movie for movie in data['results'] 
                        if (movie.get('vote_average', 0) >= 6.0 and 
                            movie.get('poster_path') and
                            movie.get('overview') and
                            str(movie.get('id')) not in seen_movies)
                    ]
                    
                    if not valid_movies:
                        continue
                    
                    movie = random.choice(valid_movies)
                    movie_id = movie.get('id')
                    
                    # Buscar detalhes
                    details_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=pt-BR"
                    details_response = requests.get(details_url, timeout=5)
                    
                    if details_response.status_code != 200:
                        continue
                    
                    details_data = details_response.json()
                    
                    # Extrair gêneros
                    genres = []
                    if details_data.get('genres'):
                        genres = [genre['name'] for genre in details_data['genres']]
                    
                    # BUSCAR TRAILER
                    trailer_url = get_movie_trailer(movie_id)
                    
                    # Tratamento de campos
                    vote_average = movie.get('vote_average', 0)
                    if vote_average is None:
                        vote_average = 0
                        
                    release_date = movie.get('release_date', '')
                    release_year = release_date.split('-')[0] if release_date else ''
                    
                    return jsonify({
                        'title': movie.get('title', 'Título não disponível'),
                        'backdrop_path': f"https://image.tmdb.org/t/p/original{movie.get('backdrop_path', '')}",
                        'poster_path': f"https://image.tmdb.org/t/p/w500{movie.get('poster_path', '')}",
                        'overview': movie.get('overview', 'Descrição não disponível'),
                        'id': movie_id,
                        'vote_average': round(vote_average, 1),
                        'release_year': release_year,
                        'genres': genres,
                        'category': chosen_category,
                        'trailer_url': trailer_url,
                        'attempts': attempt + 1,
                        'total_seen': len(seen_movies)
                    })
                    
            except requests.exceptions.Timeout:
                continue
            except Exception as e:
                continue
        
        # Se chegou aqui, não encontrou filmes novos
        return jsonify({
            'error': 'Você já reagiu a todos os filmes disponíveis!',
            'total_seen': len(seen_movies)
        }), 404
        
    except Exception as e:
        print(f"💥 Erro crítico: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@movies_bp.route('/action', methods=['POST'])
def register_action():
    """Registra a ação do usuário no banco de dados E verifica matches"""
    try:
        # Verificar se usuário está logado
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não logado'}), 401
        
        data = request.get_json()
        movie_id = data.get('movie_id')
        action = data.get('action')
        user_id = session['user_id']
        
        # Acessar Database
        db = current_app.extensions.get('db')
        if db is None:
            return jsonify({'error': 'Database não configurado'}), 500
        
        # Inserir ou atualizar a reação
        # PostgreSQL usa ON CONFLICT em vez de ON DUPLICATE KEY
        db.session.execute(
            text("""
                INSERT INTO MoviesReacted (user_id, movie_id, action) 
                VALUES (:user_id, :movie_id, :action)
                ON CONFLICT (user_id, movie_id) 
                DO UPDATE SET action = EXCLUDED.action, reacted_at = CURRENT_TIMESTAMP
            """),
            {'user_id': user_id, 'movie_id': movie_id, 'action': action}
        )
        
        db.session.commit()
        
        # 🎯 CHECAR MATCHES APÓS REGISTRAR AÇÃO
        if action in ['like', 'indicate']:
            check_and_create_matches(user_id, movie_id, action)
        
        return jsonify({
            'status': 'success', 
            'action': action, 
            'movie_id': movie_id,
            'message': f'Ação {action} registrada com sucesso'
        })
        
    except Exception as e:
        print(f"Erro na rota /action: {str(e)}")
        if 'db' in locals():
            db.session.rollback()
        return jsonify({'error': str(e)}), 500