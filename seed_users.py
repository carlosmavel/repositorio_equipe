# seed_users.py
from werkzeug.security import generate_password_hash
try:
    from .database import db  # pragma: no cover
except ImportError:
    from database import db
try:
    from .models import User, Celula, Funcao
except ImportError:  # pragma: no cover - fallback for direct execution
    from models import User, Celula, Funcao
from app import app      # importa o Flask já configurado
# from datetime import date # Se você for adicionar datas como data_admissao

def run():
    users_data = [
        dict(
            username="admin",
            email="admin@seudominio.com", # E-mail adicionado
            password_hash=generate_password_hash("Admin123!"),
            funcoes=["admin"],
            nome_completo="Admin de Souza",
            matricula="ADM001",
            cpf="000.000.000-00", # Exemplo, coloque dados fictícios
            # Novos campos organizacionais como None por enquanto
            estabelecimento_id=None,
            setor_id=None,
            cargo_id=None,
            # Outros campos opcionais
            # data_admissao=date(2020, 1, 15),
            # ramal="1000"
        ),
        dict(
            username="adminglobal",
            email="adminglobal@seudominio.com",
            password_hash=generate_password_hash("Admin123!"),
            funcoes=["admin"],
            nome_completo="Administrador Global",
            matricula="ADM000",
            cpf="999.999.999-99",
            estabelecimento_id=None,
            setor_id=None,
            cargo_id=None,
        ),
        dict(
            username="colaborador",
            email="colaborador@seudominio.com",  # E-mail adicionado
            password_hash=generate_password_hash("Colab123!"),
            nome_completo="João Silva",
            matricula="COL001",
            cpf="222.222.222-22",  # Exemplo
            estabelecimento_id=None,
            setor_id=None,
            cargo_id=None,
        )
    ]

    with app.app_context():  # Garante o contexto da aplicação Flask
        print("Verificando e criando usuários de exemplo...")

        celula = Celula.query.filter_by(nome="Célula Exemplo").first()

        for user_data in users_data:
            user = User.query.filter_by(username=user_data["username"]).first()
            if not user:
                if celula:
                    user_data["celula_id"] = celula.id
                    user_data["setor_id"] = celula.setor_id
                    user_data["estabelecimento_id"] = celula.estabelecimento_id

                perms = user_data.pop("funcoes", [])
                new_user = User(**user_data)
                for code in perms:
                    func = Funcao.query.filter_by(codigo=code).first()
                    if func:
                        new_user.permissoes_personalizadas.append(func)
                db.session.add(new_user)
                print(f"Usuário {user_data['username']} criado.")
            else:
                print(f"Usuário {user_data['username']} já existe.")
        
        db.session.commit()
        print("🚀 Seed de usuários concluído.")

if __name__ == "__main__":
    run()