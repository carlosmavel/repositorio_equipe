from functools import wraps
from flask import session, redirect, url_for, flash, request
try:
    from .models import User
except ImportError:  # pragma: no cover
    from core.models import User


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
