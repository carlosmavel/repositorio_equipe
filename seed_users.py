# seed_users.py
from werkzeug.security import generate_password_hash
from database import db
from models import User
from app import app                # importa o Flask já configurado

def run():
    users = [
        dict(username="admin",  password_hash=generate_password_hash("Admin123!"),  role="admin",       nome_completo="Admin de Souza"),
        dict(username="editor", password_hash=generate_password_hash("Editor123!"), role="editor",      nome_completo="Maria Oliveira"),
        dict(username="colaborador",  password_hash=generate_password_hash("Colab123!"),  role="colaborador", nome_completo="João Silva"),
    ]

    with app.app_context():       # garante o contexto
        for data in users:
            if not User.query.filter_by(username=data["username"]).first():
                db.session.add(User(**data))
        db.session.commit()
        print("🚀 Usuários de exemplo criados (ou já existiam).")

if __name__ == "__main__":
    run()