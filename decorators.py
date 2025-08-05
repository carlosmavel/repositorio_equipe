from functools import wraps
from flask import session, redirect, url_for, flash, request
try:
    from .models import User
except ImportError:  # pragma: no cover
    from models import User
try:
    from .utils import user_can_access_form_builder
except ImportError:  # pragma: no cover
    from utils import user_can_access_form_builder


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login', next=request.url))
        user = User.query.get(session['user_id'])
        if not user or not user.has_permissao('admin'):
            flash('Acesso negado. Você precisa ser um administrador para acessar esta página.', 'danger')
            return redirect(url_for('meus_artigos'))
        return f(*args, **kwargs)
    return decorated_function


def form_builder_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login', next=request.url))
        user = User.query.get(session['user_id'])
        if not user_can_access_form_builder(user):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('pagina_inicial'))
        return f(*args, **kwargs)
    return decorated_function
