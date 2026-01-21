# dataroutes.py
from flask import Blueprint, render_template
from server.utils.auth import login_required 


# Define seu blueprint corretamente
page_bp = Blueprint('page', __name__)

# Rotas para os arquivos index

@page_bp.route('/')
@login_required
def index():
    return render_template('index.html')



