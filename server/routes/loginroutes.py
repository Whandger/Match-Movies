from flask import Blueprint, redirect, render_template, request, session, jsonify, current_app, url_for
from werkzeug.security import generate_password_hash, check_password_hash
# REMOVER: from sqlalchemy import text  # NÃO precisa mais aqui

# IMPORTAR do users.py atualizado
from server.utils.users import get_user_by_username_or_email, insert_user

login_bp = Blueprint('login', __name__)

# REMOVER estas funções (já estão no users.py):
# def get_user_by_username_or_email(username, email):
#     ...
# 
# def insert_user(email, username, hashed_password):
#     ...

@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        # Acessa com segurança a extensão db (SQLAlchemy)
        db = current_app.extensions.get('db')
        if db is None:
            return jsonify({'success': False, 'message': 'Database não está configurado'}), 500

        # Busca usuário usando a função do users.py
        user = get_user_by_username_or_email(username, username)

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return jsonify({'success': True}), 200
        else:
            return jsonify({'success': False, 'message': 'Login inválido'}), 401

    return render_template('login.html')


@login_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')

    if not email or not username or not password:
        return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios'}), 400

    db = current_app.extensions.get('db')
    if db is None:
        return jsonify({'success': False, 'message': 'Database não está configurado'}), 500

    # Verifica se usuário já existe
    existing_user = get_user_by_username_or_email(username, email)
    if existing_user:
        return jsonify({'success': False, 'message': 'Usuário ou email já existe'}), 409

    # Insere novo usuário
    hashed_password = generate_password_hash(password)
    success = insert_user(email, username, hashed_password)
    
    if success:
        return jsonify({'success': True}), 201
    else:
        return jsonify({'success': False, 'message': 'Erro ao criar usuário'}), 500

@login_bp.route('/alguma-rota')
def alguma_rota():
    username = session.get('username')
    return render_template('seu_template.html', username=username)

# Logout
@login_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('login.login'))