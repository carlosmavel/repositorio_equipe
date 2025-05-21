# seed_users.py

import os
import sys
from getpass import getpass

# Ajuste este import de acordo com seu layout de pacotes
from app import app, db
from models import User

def create_user(username, password, role, nome_completo):
    if User.query.filter_by(username=username).first():
        print(f"Usuário '{username}' já existe, pulando.")
        return
    user = User(
        username=username,
        role=role,
        nome_completo=nome_completo
    )
    user.set_password(password)
    db.session.add(user)
    print(f"Usuário criado: {username} [{role}]")

if __name__ == '__main__':
    # Precisamos do contexto da aplicação
    with app.app_context():
        db.create_all()  # garante que as tables existam
        print("Inserção de usuários iniciais\n")

        # Admin
        admin_user = os.environ.get('SEED_ADMIN_USER') or input("Admin username [admin]: ") or "admin"
        admin_pass = os.environ.get('SEED_ADMIN_PASS') or getpass(f"Senha para '{admin_user}': ")
        create_user(admin_user, admin_pass, role="admin", nome_completo="Administrador")

        # Editor
        editor_user = os.environ.get('SEED_EDITOR_USER') or input("\nEditor username [editor]: ") or "editor"
        editor_pass = os.environ.get('SEED_EDITOR_PASS') or getpass(f"Senha para '{editor_user}': ")
        create_user(editor_user, editor_pass, role="editor", nome_completo="Editor Padrão")

        # Colaborador
        collab_user = os.environ.get('SEED_COLLAB_USER') or input("\nColaborador username [colab]: ") or "colab"
        collab_pass = os.environ.get('SEED_COLLAB_PASS') or getpass(f"Senha para '{collab_user}': ")
        create_user(collab_user, collab_pass, role="colaborador", nome_completo="Colaborador Padrão")

        db.session.commit()
        print("\nTodos os usuários seed foram inseridos (ou existentes).")