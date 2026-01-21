from functools import wraps
from flask import redirect, url_for, session

def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session: # Checa se o usuario esta na sessão usando "session" do flask
            return redirect(url_for('login.login'))  # Se o usuario não estiver logado envia para o (blueprint.login) | Tela de login
        return view_func(*args, **kwargs)
    return wrapper