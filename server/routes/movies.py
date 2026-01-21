from flask import Blueprint, jsonify, session, request, current_app
from sqlalchemy import text
import requests
import random
import json
from datetime import datetime

movies_bp = Blueprint('movies', __name__)

TMDB_API_KEY = '941fae9e612c2f209e18d77a5a760269'

# ============================================================================
# SISTEMA DE MATCHES - VERSÃO FINAL
# ============================================================================

def check_and_create_matches(user_id, movie_id, action):
    """Verifica e cria matches quando dois usuários reagem ao mesmo filme"""
    try:
        # Só verifica matches para likes e indicações
        if action not in ['like', 'indicate']:
            return
        
        db = current_app.extensions.get('db')
        if db is None:
            print("❌ ERROR: Database não encontrado")
            return
        
        print(f"🔄 CHECK MATCHES: user={user_id}, movie={movie_id}, action={action}")
        
        # Buscar todas as conexões ativas do usuário
        connections = db.session.execute(
            text("""
                SELECT id, user1_id, user2_id 
                FROM "UserConnections" 
                WHERE (user1_id = :user_id OR user2_id = :user_id) 
                AND is_active = TRUE
            """),
            {'user_id': user_id}
        ).fetchall()
        
        print(f"📊 Conexões encontradas: {len(connections)}")
        
        for connection in connections:
            connection_id = connection[0]
            user1_id = connection[1]
            user2_id = connection[2]
            
            # Determinar quem é o parceiro
            partner_id = user2_id if user1_id == user_id else user1_id
            
            print(f"🔍 Verificando conexão {connection_id} com parceiro {partner_id}")
            
            # Verificar se o parceiro também curtiu/indicou este filme
            partner_reaction = db.session.execute(
                text("""
                    SELECT COUNT(*) 
                    FROM "MoviesReacted" 
                    WHERE user_id = :partner_id 
                    AND movie_id = :movie_id 
                    AND action IN ('like', 'indicate')
                """),
                {'partner_id': partner_id, 'movie_id': movie_id}
            ).scalar()
            
            print(f"📌 Parceiro {partner_id} reagiu ao filme {movie_id}? {partner_reaction > 0}")
            
            if partner_reaction > 0:
                print(f"🎉 MATCH ENCONTRADO! Usuários {user_id} e {partner_id} curtiram o filme {movie_id}")
                
                # Buscar os matches atuais
                current_matches = db.session.execute(
                    text("""
                        SELECT matched_movies 
                        FROM "UserConnections" 
                        WHERE id = :connection_id
                    """),
                    {'connection_id': connection_id}
                ).scalar()
                
                # Converter para lista Python (JSONB pode vir como lista ou string)
                if current_matches is None:
                    matches_list = []
                elif isinstance(current_matches, str):
                    matches_list = json.loads(current_matches)
                else:
                    matches_list = current_matches
                
                print(f"📋 Matches atuais: {matches_list}")
                
                # Verificar se este filme já está na lista de matches
                if movie_id not in matches_list:
                    matches_list.append(movie_id)
                    
                    # Atualizar a conexão com o novo match
                    db.session.execute(
                        text("""
                            UPDATE "UserConnections" 
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
                    
                    print(f"✅ NOVO MATCH REGISTRADO: Conexão {connection_id}, Filme {movie_id}")
        
        db.session.commit()
        
    except Exception as e:
        print(f"❌ ERROR ao verificar matches: {str(e)}")
        import traceback
        traceback.print_exc()
        if 'db' in locals():
            db.session.rollback()

# ============================================================================
# ROTA PARA REGISTRAR AÇÃO
# ============================================================================

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
        
        if not movie_id or not action:
            return jsonify({'success': False, 'error': 'Dados incompletos'}), 400
        
        print(f"🎬 REGISTER ACTION: user={user_id}, movie={movie_id}, action={action}")
        
        # Acessar Database
        db = current_app.extensions.get('db')
        if db is None:
            return jsonify({'error': 'Database não configurado'}), 500
        
        # Inserir ou atualizar a reação
        db.session.execute(
            text("""
                INSERT INTO "MoviesReacted" (user_id, movie_id, action, reacted_at) 
                VALUES (:user_id, :movie_id, :action, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, movie_id) 
                DO UPDATE SET action = EXCLUDED.action, reacted_at = CURRENT_TIMESTAMP
            """),
            {'user_id': user_id, 'movie_id': movie_id, 'action': action}
        )
        
        db.session.commit()
        
        # 🎯 CHECAR MATCHES APÓS REGISTRAR AÇÃO
        if action in ['like', 'indicate']:
            print(f"🔄 Verificando matches para ação {action}...")
            check_and_create_matches(user_id, movie_id, action)
        
        return jsonify({
            'success': True,
            'action': action, 
            'movie_id': movie_id,
            'message': f'Ação {action} registrada com sucesso'
        })
        
    except Exception as e:
        print(f"❌ ERROR na rota /action: {str(e)}")
        import traceback
        traceback.print_exc()
        if 'db' in locals():
            db.session.rollback()
        return jsonify({'success': False, 'error': str(e)[:100]}), 500

# ============================================================================
# ROTA PARA BUSCAR MATCHES
# ============================================================================

@movies_bp.route('/matches')
def get_matches():
    """Retorna todos os matches do usuário logado"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não logado'}), 401
        
        user_id = session['user_id']
        db = current_app.extensions.get('db')
        
        if db is None:
            return jsonify({'error': 'Database não configurado'}), 500
        
        print(f"🔍 BUSCANDO MATCHES para user_id={user_id}")
        
        # Buscar conexões com matches
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
                FROM "UserConnections" uc
                JOIN "MoviesUsers" mu ON mu.id = CASE 
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
        all_matches = []
        
        for row in connections_data:
            connection_id = row[0]
            match_count = row[1]
            last_match_at = row[2]
            matched_movies = row[3]
            partner_id = row[4]
            partner_username = row[5]
            
            # Converter matched_movies para lista
            if matched_movies is None:
                movies_list = []
            elif isinstance(matched_movies, str):
                movies_list = json.loads(matched_movies)
            else:
                movies_list = matched_movies
            
            print(f"📋 Conexão {connection_id} tem {len(movies_list)} matches: {movies_list}")
            
            # Adicionar cada filme como um match separado
            for movie_id in movies_list:
                all_matches.append({
                    'connection_id': connection_id,
                    'movie_id': movie_id,
                    'partner_id': partner_id,
                    'partner_username': partner_username,
                    'match_count': match_count,
                    'last_match_at': last_match_at.isoformat() if last_match_at else None
                })
        
        print(f"✅ Total de matches encontrados: {len(all_matches)}")
        
        return jsonify({
            'success': True,
            'matches': all_matches,
            'total_matches': len(all_matches)
        })
        
    except Exception as e:
        print(f"❌ ERROR ao buscar matches: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)[:100]}), 500

# ============================================================================
# ROTA PARA OBTER DETALHES DE UM FILME
# ============================================================================

@movies_bp.route('/movie/<int:movie_id>')
def get_movie_details(movie_id):
    """Retorna detalhes de um filme específico"""
    try:
        # Buscar detalhes do TMDB
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=pt-BR"
        response = requests.get(url, timeout=5)
        
        if response.status_code != 200:
            return jsonify({'success': False, 'error': 'Filme não encontrado'}), 404
        
        movie_data = response.json()
        
        # Buscar trailer
        trailer_url = None
        videos_url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos"
        videos_response = requests.get(
            videos_url,
            params={'api_key': TMDB_API_KEY, 'language': 'pt-BR'},
            timeout=5
        )
        
        if videos_response.status_code == 200:
            videos_data = videos_response.json()
            for video in videos_data.get('results', []):
                if video.get('type') == 'Trailer' and video.get('site') == 'YouTube':
                    youtube_key = video.get('key')
                    if youtube_key:
                        trailer_url = f"https://www.youtube.com/watch?v={youtube_key}"
                        break
        
        return jsonify({
            'success': True,
            'movie': {
                'id': movie_data.get('id'),
                'title': movie_data.get('title', 'Título não disponível'),
                'overview': movie_data.get('overview', 'Descrição não disponível'),
                'poster_path': f"https://image.tmdb.org/t/p/w500{movie_data.get('poster_path', '')}" if movie_data.get('poster_path') else '',
                'backdrop_path': f"https://image.tmdb.org/t/p/original{movie_data.get('backdrop_path', '')}" if movie_data.get('backdrop_path') else '',
                'release_date': movie_data.get('release_date', ''),
                'vote_average': round(movie_data.get('vote_average', 0), 1),
                'genres': [genre['name'] for genre in movie_data.get('genres', [])],
                'trailer_url': trailer_url
            }
        })
        
    except Exception as e:
        print(f"❌ ERROR ao buscar detalhes do filme: {str(e)}")
        return jsonify({'success': False, 'error': str(e)[:100]}), 500

# ============================================================================
# SISTEMA DE FILMES ALEATÓRIOS (mantido)
# ============================================================================

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
            
            for video in videos_data.get('results', []):
                if video.get('type') == 'Trailer' and video.get('site') == 'YouTube':
                    youtube_key = video.get('key')
                    if youtube_key:
                        return f"https://www.youtube.com/watch?v={youtube_key}"
            
            for video in videos_data.get('results', []):
                if video.get('site') == 'YouTube' and video.get('key'):
                    youtube_key = video.get('key')
                    return f"https://www.youtube.com/watch?v={youtube_key}"
        
        return None
        
    except Exception as e:
        print(f"Erro ao buscar trailer: {e}")
        return None

@movies_bp.route('/random')
def random_movie():
    """Busca um filme aleatório que o usuário ainda não reagiu"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não logado'}), 401
        
        user_id = session['user_id']
        db = current_app.extensions.get('db')
        
        if db is None:
            return jsonify({'error': 'Database não configurado'}), 500
        
        print(f"🎲 Buscando filme aleatório para user_id={user_id}")
        
        # Buscar filmes que o usuário já reagiu
        seen_movies_result = db.session.execute(
            text('SELECT movie_id FROM "MoviesReacted" WHERE user_id = :user_id'),
            {'user_id': user_id}
        ).fetchall()
        
        seen_movies = [str(row[0]) for row in seen_movies_result]
        
        print(f"📊 Usuário já viu {len(seen_movies)} filmes")
        
        # Categorias
        categories = {
            "popular": 700,
            "top_rated": 700, 
            "now_playing": 10,
            "upcoming": 10
        }
        
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
                    
                    details_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=pt-BR"
                    details_response = requests.get(details_url, timeout=5)
                    
                    if details_response.status_code != 200:
                        continue
                    
                    details_data = details_response.json()
                    
                    genres = []
                    if details_data.get('genres'):
                        genres = [genre['name'] for genre in details_data['genres']]
                    
                    trailer_url = get_movie_trailer(movie_id)
                    
                    vote_average = movie.get('vote_average', 0)
                    if vote_average is None:
                        vote_average = 0
                        
                    release_date = movie.get('release_date', '')
                    release_year = release_date.split('-')[0] if release_date else ''
                    
                    print(f"✅ Filme encontrado: {movie.get('title')}")
                    
                    return jsonify({
                        'success': True,
                        'title': movie.get('title', 'Título não disponível'),
                        'backdrop_path': f"https://image.tmdb.org/t/p/original{movie.get('backdrop_path', '')}" if movie.get('backdrop_path') else '',
                        'poster_path': f"https://image.tmdb.org/t/p/w500{movie.get('poster_path', '')}" if movie.get('poster_path') else '',
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
        
        return jsonify({
            'success': False,
            'error': 'Você já reagiu a todos os filmes disponíveis!',
            'total_seen': len(seen_movies)
        }), 404
        
    except Exception as e:
        print(f"❌ ERROR crítico: {str(e)}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

# ============================================================================
# SISTEMA DE CONEXÃO (mantido)
# ============================================================================

@movies_bp.route('/connect', methods=['POST'])
def connect_users():
    """Conecta dois usuários"""
    try:
        print("🔗 /connect rota chamada")
        
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Usuário não logado'}), 401
        
        current_user_id = session['user_id']
        data = request.get_json()
        target_user_id = data.get('target_user_id')
        
        if not target_user_id:
            return jsonify({'success': False, 'message': 'ID do usuário alvo é obrigatório'}), 400
        
        try:
            target_user_id = int(target_user_id)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'ID do usuário deve ser um número'}), 400
        
        if current_user_id == target_user_id:
            return jsonify({'success': False, 'message': 'Não é possível conectar consigo mesmo'}), 400
        
        db = current_app.extensions.get('db')
        if db is None:
            return jsonify({'success': False, 'message': 'Database não configurado'}), 500
        
        print(f"🔍 Verificando usuário alvo: {target_user_id}")
        
        target_user = db.session.execute(
            text('SELECT id, username FROM "MoviesUsers" WHERE id = :target_id'),
            {'target_id': target_user_id}
        ).fetchone()
        
        if not target_user:
            return jsonify({'success': False, 'message': 'Usuário não encontrado'}), 404
        
        print(f"✅ Usuário alvo encontrado: {target_user[1]}")
        
        existing_connection = db.session.execute(
            text("""
                SELECT id FROM "UserConnections" 
                WHERE (user1_id = :user1 AND user2_id = :user2) 
                   OR (user1_id = :user2 AND user2_id = :user1)
            """),
            {'user1': current_user_id, 'user2': target_user_id}
        ).fetchone()
        
        if existing_connection:
            return jsonify({'success': False, 'message': 'Já existe uma conexão com este usuário'}), 400
        
        user1_id = min(current_user_id, target_user_id)
        user2_id = max(current_user_id, target_user_id)
        
        print(f"🔗 Criando conexão entre {user1_id} e {user2_id}")
        
        db.session.execute(
            text("""
                INSERT INTO "UserConnections" (user1_id, user2_id, match_count, matched_movies, is_active) 
                VALUES (:user1_id, :user2_id, 0, '[]', TRUE)
            """),
            {'user1_id': user1_id, 'user2_id': user2_id}
        )
        
        db.session.commit()
        
        print(f"✅ Conexão criada entre {current_user_id} e {target_user_id}")
        
        return jsonify({
            'success': True, 
            'message': 'Conexão estabelecida com sucesso!',
            'partner_id': target_user_id,
            'partner_username': target_user[1]
        })
        
    except Exception as e:
        print(f"❌ ERROR na conexão: {str(e)}")
        if 'db' in locals():
            db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro interno do servidor: {str(e)[:100]}'}), 500

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
        
        print(f"🔍 Buscando conexões para user_id={current_user_id}")
        
        connections = db.session.execute(
            text("""
                SELECT 
                    uc.id,
                    CASE 
                        WHEN uc.user1_id = :user_id THEN uc.user2_id 
                        ELSE uc.user1_id 
                    END as partner_id,
                    mu.username as partner_username,
                    uc.connected_at,
                    uc.match_count
                FROM "UserConnections" uc
                JOIN "MoviesUsers" mu ON mu.id = CASE 
                    WHEN uc.user1_id = :user_id THEN uc.user2_id 
                    ELSE uc.user1_id 
                END
                WHERE (uc.user1_id = :user_id OR uc.user2_id = :user_id) AND uc.is_active = TRUE
                ORDER BY uc.connected_at DESC
            """),
            {'user_id': current_user_id}
        ).fetchall()
        
        connection_list = []
        for conn in connections:
            connection_list.append({
                'connection_id': conn[0],
                'partner_id': conn[1],
                'partner_username': conn[2],
                'connected_at': conn[3].isoformat() if conn[3] else None,
                'match_count': conn[4] or 0
            })
        
        print(f"✅ Encontradas {len(connection_list)} conexões")
        
        return jsonify({'connections': connection_list})
        
    except Exception as e:
        print(f"❌ ERROR ao buscar conexões: {str(e)}")
        return jsonify({'connections': []})
