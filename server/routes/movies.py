from flask import Blueprint, jsonify, session, request, current_app
from sqlalchemy import text
import requests
import random
import json
import time
from functools import wraps
from datetime import datetime

movies_bp = Blueprint('movies', __name__)

TMDB_API_KEY = '941fae9e612c2f209e18d77a5a760269'

# ============================================================================
# DECORATORS E UTILIDADES
# ============================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não logado'}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_db():
    db = current_app.extensions.get('db')
    if db is None:
        raise Exception('Database não configurado')
    return db

# ============================================================================
# FUNÇÕES AUXILIARES PARA TMDB API
# ============================================================================

def fetch_movie_details(movie_id):
    """Busca detalhes completos de um filme na TMDB API"""
    try:
        # Detalhes básicos
        details_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        details_response = requests.get(
            details_url,
            params={'api_key': TMDB_API_KEY, 'language': 'pt-BR'},
            timeout=5
        )
        
        if details_response.status_code != 200:
            return None
        
        movie_data = details_response.json()
        
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
        
        # Formatar dados
        genres = [genre['name'] for genre in movie_data.get('genres', [])]
        vote_average = movie_data.get('vote_average', 0)
        if vote_average is None:
            vote_average = 0
            
        release_date = movie_data.get('release_date', '')
        release_year = release_date.split('-')[0] if release_date else ''
        
        return {
            'title': movie_data.get('title', 'Título não disponível'),
            'backdrop_path': f"https://image.tmdb.org/t/p/original{movie_data.get('backdrop_path', '')}" if movie_data.get('backdrop_path') else '',
            'poster_path': f"https://image.tmdb.org/t/p/w500{movie_data.get('poster_path', '')}" if movie_data.get('poster_path') else '',
            'overview': movie_data.get('overview', 'Descrição não disponível'),
            'id': movie_id,
            'vote_average': round(vote_average, 1),
            'release_year': release_year,
            'genres': genres,
            'trailer_url': trailer_url,
            'runtime': movie_data.get('runtime'),
            'tagline': movie_data.get('tagline')
        }
        
    except Exception as e:
        print(f"❌ ERRO ao buscar detalhes do filme {movie_id}: {str(e)}")
        return None

def fetch_movie_details_basic(movie_id):
    """Busca apenas informações básicas do filme (rápido)"""
    try:
        response = requests.get(
            f"https://api.themoviedb.org/3/movie/{movie_id}",
            params={'api_key': TMDB_API_KEY, 'language': 'pt-BR'},
            timeout=3
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        # Extrair gêneros
        genres = []
        if 'genres' in data and data['genres']:
            genres = [genre['name'] for genre in data['genres']]
        
        # Buscar trailer rapidamente
        trailer_url = None
        try:
            videos_response = requests.get(
                f"https://api.themoviedb.org/3/movie/{movie_id}/videos",
                params={'api_key': TMDB_API_KEY, 'language': 'pt-BR'},
                timeout=2
            )
            
            if videos_response.status_code == 200:
                videos_data = videos_response.json()
                for video in videos_data.get('results', [])[:3]:
                    if video.get('type') == 'Trailer' and video.get('site') == 'YouTube':
                        youtube_key = video.get('key')
                        if youtube_key:
                            trailer_url = f"https://www.youtube.com/watch?v={youtube_key}"
                            break
        except:
            pass
        
        return {
            'genres': genres,
            'trailer_url': trailer_url
        }
        
    except Exception:
        return None

def fetch_movies_from_category(category, page, seen_movies):
    """Busca filmes de uma categoria específica"""
    try:
        url = f"https://api.themoviedb.org/3/movie/{category}?api_key={TMDB_API_KEY}&language=pt-BR&page={page}"
        response = requests.get(url, timeout=5)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        
        valid_movies = []
        for movie in data.get('results', []):
            if (movie.get('vote_average', 0) >= 6.0 and 
                movie.get('poster_path') and
                movie.get('overview') and
                str(movie.get('id')) not in seen_movies):
                
                # Converter IDs de gênero para nomes
                genres = []
                genre_ids = movie.get('genre_ids', [])
                if genre_ids:
                    genre_map = {
                        28: 'Ação', 12: 'Aventura', 16: 'Animação', 35: 'Comédia',
                        80: 'Crime', 99: 'Documentário', 18: 'Drama', 10751: 'Família',
                        14: 'Fantasia', 36: 'História', 27: 'Terror', 10402: 'Música',
                        9648: 'Mistério', 10749: 'Romance', 878: 'Ficção científica',
                        10770: 'Cinema TV', 53: 'Thriller', 10752: 'Guerra', 37: 'Faroeste'
                    }
                    genres = [genre_map.get(gid, f'Gênero {gid}') for gid in genre_ids[:3]]
                
                valid_movies.append({
                    'title': movie.get('title', 'Título não disponível'),
                    'poster_path': f"https://image.tmdb.org/t/p/w500{movie.get('poster_path', '')}" if movie.get('poster_path') else '',
                    'overview': movie.get('overview', 'Descrição não disponível'),
                    'id': movie.get('id'),
                    'vote_average': round(movie.get('vote_average', 0), 1),
                    'release_year': movie.get('release_date', '').split('-')[0] if movie.get('release_date') else '',
                    'backdrop_path': f"https://image.tmdb.org/t/p/original{movie.get('backdrop_path', '')}" if movie.get('backdrop_path') else '',
                    'genre_ids': movie.get('genre_ids', []),
                    'genres': genres,
                    'trailer_url': None
                })
        
        return valid_movies
        
    except Exception as e:
        print(f"❌ ERRO ao buscar filmes da categoria {category}: {str(e)}")
        return []

# ============================================================================
# ROTAS PRINCIPAIS DE FILMES (COM PRÉ-CARREGAMENTO)
# ============================================================================

@movies_bp.route('/random')
@movies_bp.route('/random/<int:batch_size>')
@login_required
def random_movie(batch_size=1):
    """Retorna 1 ou mais filmes aleatórios não vistos pelo usuário"""
    try:
        user_id = session['user_id']
        db = get_db()
        
        # Buscar filmes já reagidos
        seen_movies_result = db.session.execute(
            text('SELECT movie_id FROM "MoviesReacted" WHERE user_id = :user_id'),
            {'user_id': user_id}
        ).fetchall()
        
        seen_movies = [str(row[0]) for row in seen_movies_result]
        
        print(f"🔍 Usuário {user_id} já viu {len(seen_movies)} filmes")
        
        # Se batch_size for 1, busca um filme otimizado para velocidade
        if batch_size == 1:
            movie = fetch_single_random_movie_optimized(seen_movies)
            if movie:
                print(f"✅ Filme encontrado: {movie['title']}")
                return jsonify({
                    'success': True,
                    'movie': movie,
                    'batch_size': 1,
                    'is_batch': False,
                    'total_seen': len(seen_movies)
                })
            else:
                print(f"❌ Nenhum filme encontrado após tentativas")
                return jsonify({
                    'success': False,
                    'error': 'Não foi possível encontrar um filme',
                    'total_seen': len(seen_movies)
                }), 404
        
        # Se batch_size > 1, busca múltiplos filmes
        else:
            movies = fetch_batch_random_movies(seen_movies, batch_size)
            if movies:
                print(f"✅ {len(movies)} filmes encontrados para pré-carregamento")
                return jsonify({
                    'success': True,
                    'movies': movies,
                    'batch_size': len(movies),
                    'is_batch': True,
                    'total_seen': len(seen_movies)
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Não foi possível carregar filmes',
                    'total_seen': len(seen_movies)
                }), 404
        
    except Exception as e:
        print(f"❌ ERRO em /random: {str(e)}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

def fetch_single_random_movie_optimized(seen_movies, max_attempts=5):
    """Busca um único filme otimizado para velocidade"""
    categories = {
        "popular": 50,
        "now_playing": 5,
    }
    
    for attempt in range(max_attempts):
        try:
            chosen_category = random.choice(list(categories.keys()))
            random_page = random.randint(1, categories[chosen_category])
            
            print(f"🔄 Tentativa {attempt+1}: Buscando em {chosen_category} página {random_page}")
            
            # Buscar filmes da categoria
            movies = fetch_movies_from_category(chosen_category, random_page, seen_movies)
            
            if movies:
                print(f"📊 Encontrados {len(movies)} filmes válidos")
                selected_movie = random.choice(movies)
                
                # Buscar detalhes básicos
                movie_details = fetch_movie_details_basic(selected_movie['id'])
                
                # Montar objeto do filme
                movie_data = {
                    'title': selected_movie['title'],
                    'poster_path': selected_movie['poster_path'],
                    'overview': selected_movie['overview'],
                    'id': selected_movie['id'],
                    'vote_average': selected_movie['vote_average'],
                    'release_year': selected_movie['release_year'],
                    'backdrop_path': selected_movie['backdrop_path'],
                    'trailer_url': None,
                    'genres': selected_movie['genres']  # Já vem com gêneros básicos
                }
                
                # Atualizar com detalhes se encontrados
                if movie_details:
                    if movie_details.get('genres'):
                        movie_data['genres'] = movie_details['genres']
                    if movie_details.get('trailer_url'):
                        movie_data['trailer_url'] = movie_details['trailer_url']
                
                return movie_data
            else:
                print(f"📭 Nenhum filme válido nesta página")
                
        except Exception as e:
            print(f"⚠️ Tentativa {attempt + 1} falhou: {str(e)}")
            continue
    
    return None

def fetch_batch_random_movies(seen_movies, batch_size=5, max_attempts=15):
    """Busca múltiplos filmes de uma vez para pré-carregamento"""
    categories = {
        "popular": 500,
        "top_rated": 500, 
        "now_playing": 15,
        "upcoming": 15
    }
    
    movies_found = []
    attempts = 0
    
    print(f"🔄 Iniciando busca batch por {batch_size} filmes")
    
    while len(movies_found) < batch_size and attempts < max_attempts:
        attempts += 1
        
        try:
            chosen_category = random.choice(list(categories.keys()))
            random_page = random.randint(1, categories[chosen_category])
            
            # Buscar filmes da categoria
            category_movies = fetch_movies_from_category(chosen_category, random_page, seen_movies)
            
            for movie in category_movies:
                if len(movies_found) >= batch_size:
                    break
                
                # Verificar se não está duplicado
                if str(movie['id']) not in [str(m['id']) for m in movies_found]:
                    # Buscar mais detalhes para o batch
                    try:
                        details = fetch_movie_details_basic(movie['id'])
                        if details:
                            if details.get('genres'):
                                movie['genres'] = details['genres']
                            if details.get('trailer_url'):
                                movie['trailer_url'] = details['trailer_url']
                    except Exception as e:
                        print(f"⚠️ Erro ao buscar detalhes para {movie['id']}: {str(e)}")
                    
                    movies_found.append(movie)
                    
            print(f"📊 Batch tentativa {attempts}: {len(movies_found)}/{batch_size} filmes")
                    
        except Exception as e:
            print(f"⚠️ Erro no batch (tentativa {attempts}): {str(e)}")
            continue
    
    print(f"✅ Batch completo: {len(movies_found)} filmes encontrados")
    return movies_found

# ============================================================================
# ROTA PARA DETALHES COMPLETOS DO FILME (LAZY LOADING)
# ============================================================================

@movies_bp.route('/movie_details/<int:movie_id>')
@login_required
def get_movie_details(movie_id):
    """Retorna detalhes completos de um filme (trailer, gêneros, etc)"""
    try:
        movie_details = fetch_movie_details(movie_id)
        
        if movie_details:
            return jsonify({
                'success': True,
                'details': {
                    'genres': movie_details['genres'],
                    'trailer_url': movie_details['trailer_url'],
                    'runtime': movie_details.get('runtime'),
                    'tagline': movie_details.get('tagline')
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Filme não encontrado'
            }), 404
        
    except Exception as e:
        print(f"❌ ERRO em /movie_details: {str(e)}")
        return jsonify({'success': False, 'error': 'Erro ao buscar detalhes'}), 500

# ============================================================================
# FUNÇÃO PRINCIPAL QUE CRIA MATCHES QUANDO O MODAL É ABERTO
# ============================================================================

def create_matches_on_modal_open():
    """Esta função é chamada quando o modal de histórico é aberto"""
    try:
        if 'user_id' not in session:
            print("❌ Usuário não logado")
            return False
        
        user_id = session['user_id']
        db = get_db()
        
        print(f"\n🎯 MODAL ABERTO - CRIANDO MATCHES PARA USER {user_id}")
        
        # Buscar todas as conexões do usuário
        connections = db.session.execute(
            text("""
                SELECT id, user1_id, user2_id 
                FROM "UserConnections" 
                WHERE (user1_id = :user_id OR user2_id = :user_id) 
                AND is_active = TRUE
            """),
            {'user_id': user_id}
        ).fetchall()
        
        total_matches_created = 0
        
        for conn in connections:
            connection_id = conn[0]
            user1_id = conn[1]
            user2_id = conn[2]
            
            print(f"\n🔍 Processando conexão {connection_id} entre {user1_id} e {user2_id}")
            
            # 1. Buscar filmes que user1 curtiu
            user1_movies_result = db.session.execute(
                text("""
                    SELECT movie_id 
                    FROM "MoviesReacted" 
                    WHERE user_id = :user_id AND action IN ('like', 'indicate')
                """),
                {'user_id': user1_id}
            ).fetchall()
            
            user1_movies = [str(row[0]) for row in user1_movies_result]
            print(f"   User {user1_id} curtiu {len(user1_movies)} filmes")
            
            # 2. Buscar filmes que user2 curtiu
            user2_movies_result = db.session.execute(
                text("""
                    SELECT movie_id 
                    FROM "MoviesReacted" 
                    WHERE user_id = :user_id AND action IN ('like', 'indicate')
                """),
                {'user_id': user2_id}
            ).fetchall()
            
            user2_movies = [str(row[0]) for row in user2_movies_result]
            print(f"   User {user2_id} curtiu {len(user2_movies)} filmes")
            
            # 3. Encontrar filmes em comum
            common_movies = []
            for movie_id in user1_movies:
                if movie_id in user2_movies:
                    common_movies.append(int(movie_id))
            
            print(f"   🎬 Filmes em comum encontrados: {len(common_movies)}")
            
            if common_movies:
                # 4. Salvar no campo matched_movies da tabela UserConnections
                db.session.execute(
                    text("""
                        UPDATE "UserConnections" 
                        SET match_count = :match_count,
                            last_match_at = CURRENT_TIMESTAMP,
                            matched_movies = :matched_movies
                        WHERE id = :connection_id
                    """),
                    {
                        'match_count': len(common_movies),
                        'matched_movies': json.dumps(common_movies),
                        'connection_id': connection_id
                    }
                )
                
                db.session.commit()
                print(f"   ✅ {len(common_movies)} matches salvos no banco!")
                total_matches_created += len(common_movies)
            else:
                print("   📭 Nenhum filme em comum")
        
        print(f"\n🎉 TOTAL DE MATCHES CRIADOS: {total_matches_created}")
        return True
        
    except Exception as e:
        print(f"❌ ERRO ao criar matches: {str(e)}")
        import traceback
        traceback.print_exc()
        if 'db' in locals():
            db.session.rollback()
        return False

# ============================================================================
# ROTA QUE O FRONTEND CHAMA QUANDO ABRE O MODAL
# ============================================================================

@movies_bp.route('/check_and_create_matches', methods=['POST'])
@login_required
def check_and_create_matches_route():
    """Rota chamada quando o modal de histórico é aberto"""
    try:
        print("\n📞 FRONTEND CHAMOU: Modal de histórico aberto!")
        
        # Chamar a função que cria os matches
        success = create_matches_on_modal_open()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Matches verificados e criados com sucesso!'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Erro ao criar matches'
            })
        
    except Exception as e:
        print(f"❌ ERRO na rota: {str(e)}")
        return jsonify({'success': False, 'error': str(e)[:200]}), 500

# ============================================================================
# ROTA PARA BUSCAR MATCHES (chamada pelo frontend para mostrar no modal)
# ============================================================================

@movies_bp.route('/matches')
@login_required
def get_matches():
    """Retorna todos os matches do usuário logado - PARA MOSTRAR NO MODAL"""
    try:
        user_id = session['user_id']
        db = get_db()

        print(f"\n🔍 Buscando matches para user_id={user_id}")

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

        print(f"📊 Conexões com matches: {len(connections_data)}")

        all_matches = []

        for row in connections_data:
            connection_id = row[0]
            match_count = row[1]
            last_match_at = row[2]
            matched_movies = row[3]
            partner_id = row[4]
            partner_username = row[5]

            # Converter matched_movies para lista
            movies_list = []
            if matched_movies:
                if isinstance(matched_movies, str):
                    try:
                        movies_list = json.loads(matched_movies)
                    except:
                        movies_list = []
                else:
                    movies_list = matched_movies

            for movie_id in movies_list:
                all_matches.append({
                    'connection_id': connection_id,
                    'movie_id': movie_id,
                    'partner_id': partner_id,
                    'partner_username': partner_username,
                    'match_count': match_count,
                    'last_match_at': last_match_at.isoformat() if last_match_at else None
                })

        print(f"\n✅ TOTAL DE MATCHES: {len(all_matches)}")

        return jsonify({
            'success': True,
            'matches': all_matches,
            'total_matches': len(all_matches)
        })

    except Exception as e:
        print(f"❌ ERRO ao buscar matches: {str(e)}")
        return jsonify({'success': False, 'error': str(e)[:200]}), 500

# ============================================================================
# ROTAS PARA REGISTRAR AÇÃO DE FILMES
# ============================================================================

@movies_bp.route('/action', methods=['POST'])
@login_required
def register_action():
    """Registra a ação do usuário no banco de dados"""
    try:
        data = request.get_json()
        movie_id = data.get('movie_id')
        action = data.get('action')
        user_id = session['user_id']
        
        if not movie_id or not action:
            return jsonify({'success': False, 'error': 'Dados incompletos'}), 400
        
        print(f"\n🎬 Registrando ação: user={user_id}, movie={movie_id}, action={action}")
        
        db = get_db()
        
        # Converter para string
        movie_id_str = str(movie_id)
        
        # Inserir ou atualizar reação
        db.session.execute(
            text("""
                INSERT INTO "MoviesReacted" (user_id, movie_id, action, reacted_at) 
                VALUES (:user_id, :movie_id, :action, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, movie_id) 
                DO UPDATE SET action = EXCLUDED.action, reacted_at = CURRENT_TIMESTAMP
            """),
            {'user_id': user_id, 'movie_id': movie_id_str, 'action': action}
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'action': action, 
            'movie_id': movie_id,
            'message': f'Ação {action} registrada com sucesso'
        })
        
    except Exception as e:
        print(f"❌ ERRO na rota /action: {str(e)}")
        if 'db' in locals():
            db.session.rollback()
        return jsonify({'success': False, 'error': str(e)[:200]}), 500

# ============================================================================
# ROTAS DE CONEXÃO
# ============================================================================

@movies_bp.route('/connect', methods=['POST'])
@login_required
def connect_users():
    """Conecta dois usuários"""
    try:
        print("\n🔗 /connect ROTA CHAMADA")
        
        current_user_id = session['user_id']
        data = request.get_json()
        target_user_id = data.get('target_user_id')
        
        if not target_user_id:
            return jsonify({'success': False, 'message': 'ID do usuário alvo é obrigatório'}), 400
        
        try:
            target_user_id = int(target_user_id)
        except:
            return jsonify({'success': False, 'message': 'ID do usuário deve ser um número'}), 400
        
        if current_user_id == target_user_id:
            return jsonify({'success': False, 'message': 'Não é possível conectar consigo mesmo'}), 400
        
        db = get_db()
        
        target_user = db.session.execute(
            text('SELECT id, username FROM "MoviesUsers" WHERE id = :target_id'),
            {'target_id': target_user_id}
        ).fetchone()
        
        if not target_user:
            return jsonify({'success': False, 'message': 'Usuário não encontrado'}), 404
        
        # Verificar se já existe conexão
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
        
        # Criar conexão
        db.session.execute(
            text("""
                INSERT INTO "UserConnections" (user1_id, user2_id, match_count, matched_movies, is_active) 
                VALUES (:user1_id, :user2_id, 0, '[]', TRUE)
            """),
            {'user1_id': user1_id, 'user2_id': user2_id}
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Conexão estabelecida com sucesso!',
            'partner_id': target_user_id,
            'partner_username': target_user[1]
        })
        
    except Exception as e:
        print(f"❌ ERRO na conexão: {str(e)}")
        if 'db' in locals():
            db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)[:200]}'}), 500

# ============================================================================
# ROTA PARA CONEXÕES ATIVAS
# ============================================================================

@movies_bp.route('/connections')
@login_required
def get_user_connections():
    """Retorna as conexões ativas do usuário"""
    try:
        current_user_id = session['user_id']
        db = get_db()
        
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
        
        return jsonify({'connections': connection_list})
        
    except Exception as e:
        print(f"❌ ERRO ao buscar conexões: {str(e)}")
        return jsonify({'connections': []})

# ============================================================================
# ROTA PARA ESTATÍSTICAS DO USUÁRIO
# ============================================================================

@movies_bp.route('/stats')
@login_required
def user_stats():
    """Estatísticas detalhadas do usuário"""
    try:
        user_id = session['user_id']
        db = get_db()
        
        stats = db.session.execute(
            text("""
                SELECT 
                    -- Totais
                    COUNT(*) as total_reactions,
                    SUM(CASE WHEN action = 'like' THEN 1 ELSE 0 END) as total_likes,
                    SUM(CASE WHEN action = 'dislike' THEN 1 ELSE 0 END) as total_dislikes,
                    SUM(CASE WHEN action = 'indicate' THEN 1 ELSE 0 END) as total_indicates,
                    
                    -- Médias
                    ROUND(AVG(CASE WHEN action = 'like' THEN 1.0 ELSE 0 END) * 100, 1) as like_percentage,
                    
                    -- Tempo
                    MIN(reacted_at) as first_reaction,
                    MAX(reacted_at) as last_reaction,
                    
                    -- Conexões
                    (SELECT COUNT(*) FROM "UserConnections" 
                     WHERE (user1_id = :user_id OR user2_id = :user_id) 
                     AND is_active = TRUE) as total_connections,
                    
                    -- Matches
                    (SELECT COALESCE(SUM(match_count), 0) FROM "UserConnections" 
                     WHERE (user1_id = :user_id OR user2_id = :user_id)) as total_matches
                    
                FROM "MoviesReacted"
                WHERE user_id = :user_id
            """),
            {'user_id': user_id}
        ).fetchone()
        
        if stats:
            stats_dict = dict(stats._mapping)
            if stats_dict['first_reaction']:
                try:
                    if isinstance(stats_dict['first_reaction'], str):
                        first_reaction = datetime.strptime(
                            stats_dict['first_reaction'], 
                            '%Y-%m-%d %H:%M:%S'
                        )
                    else:
                        first_reaction = stats_dict['first_reaction']
                    
                    days_active = (datetime.now() - first_reaction).days
                    stats_dict['days_active'] = max(1, days_active)
                    stats_dict['reactions_per_day'] = round(stats_dict['total_reactions'] / stats_dict['days_active'], 1)
                except Exception as e:
                    print(f"⚠️ Erro ao calcular dias: {str(e)}")
                    stats_dict['days_active'] = 1
                    stats_dict['reactions_per_day'] = stats_dict['total_reactions']
            else:
                stats_dict['days_active'] = 0
                stats_dict['reactions_per_day'] = 0
            
            return jsonify({
                'success': True,
                'stats': stats_dict
            })
        else:
            return jsonify({
                'success': True,
                'stats': {
                    'total_reactions': 0,
                    'total_likes': 0,
                    'total_dislikes': 0,
                    'total_indicates': 0,
                    'like_percentage': 0,
                    'total_connections': 0,
                    'total_matches': 0,
                    'days_active': 0,
                    'reactions_per_day': 0
                }
            })
        
    except Exception as e:
        print(f"❌ ERRO ao buscar estatísticas: {str(e)}")
        return jsonify({'success': False, 'error': str(e)[:200]}), 500

# ============================================================================
# ROTA DE SAÚDE DO SISTEMA
# ============================================================================

@movies_bp.route('/health')
def health_check():
    """Verifica se a API está funcionando"""
    try:
        # Verificar conexão com TMDB
        test_response = requests.get(
            f"https://api.themoviedb.org/3/movie/550",
            params={'api_key': TMDB_API_KEY},
            timeout=3
        )
        
        tmdb_status = 'ok' if test_response.status_code == 200 else 'error'
        
        # Verificar banco de dados
        db_status = 'ok'
        try:
            db = get_db()
            db.session.execute(text('SELECT 1')).fetchone()
        except:
            db_status = 'error'
        
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'tmdb': tmdb_status,
            'database': db_status,
            'version': '2.0.0'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)[:200],
            'timestamp': time.time()

        }), 500

