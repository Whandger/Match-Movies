from flask import Blueprint, redirect, render_template, request, session, jsonify, current_app, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from server.utils.users import get_user_by_username_or_email, insert_user

login_bp = Blueprint('login', __name__)

@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        print("🔄 DEBUG: /login POST chamado")
        
        data = request.get_json()
        if not data:
            print("❌ DEBUG: Nenhum JSON recebido")
            return jsonify({'success': False, 'message': 'Dados inválidos'}), 400
            
        username = data.get('username')
        password = data.get('password')
        
        print(f"🔄 DEBUG: Tentando login: username={username}")
        
        if not username or not password:
            print("❌ DEBUG: Username ou password vazios")
            return jsonify({'success': False, 'message': 'Username e password são obrigatórios'}), 400

        # Busca usuário
        user = get_user_by_username_or_email(username, username)
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            print(f"✅ DEBUG: Login bem-sucedido para: {username}")
            return jsonify({'success': True, 'username': user['username']}), 200
        else:
            print(f"❌ DEBUG: Login falhou para: {username}")
            return jsonify({'success': False, 'message': 'Credenciais inválidas'}), 401

    return render_template('login.html')

@login_bp.route('/register', methods=['POST'])
def register():
    print("🔄 DEBUG: /register endpoint chamado")
    
    data = request.get_json()
    if not data:
        print("❌ DEBUG: Nenhum JSON recebido no registro")
        return jsonify({'success': False, 'message': 'Dados inválidos'}), 400
    
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')
    
    print(f"🔄 DEBUG: Dados recebidos - username={username}, email={email}")
    
    if not email or not username or not password:
        print("❌ DEBUG: Campos obrigatórios faltando")
        return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios'}), 400

    # Verifica se usuário já existe
    print(f"🔄 DEBUG: Verificando se usuário existe: {username}")
    existing_user = get_user_by_username_or_email(username, email)
    
    if existing_user:
        print(f"❌ DEBUG: Usuário já existe: {username}")
        return jsonify({'success': False, 'message': 'Usuário ou email já existe'}), 409

    # Insere novo usuário
    print(f"🔄 DEBUG: Criando hash da senha para: {username}")
    hashed_password = generate_password_hash(password)
    
    print(f"🔄 DEBUG: Inserindo usuário no banco: {username}")
    success = insert_user(email, username, hashed_password)
    
    if success:
        print(f"✅ DEBUG: Registro bem-sucedido para: {username}")
        return jsonify({'success': True, 'message': 'Usuário criado com sucesso'}), 201
    else:
        print(f"❌ DEBUG: Falha ao inserir usuário: {username}")
        return jsonify({'success': False, 'message': 'Erro ao criar usuário'}), 500

@login_bp.route('/logout')
def logout():
    print(f"🔄 DEBUG: Logout para usuário: {session.get('username')}")
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('login.login'))
