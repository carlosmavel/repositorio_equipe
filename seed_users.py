# seed_users.py
from werkzeug.security import generate_password_hash
from database import db
from models import User # Seus modelos Estabelecimento, CentroDeCusto, etc., já estão em models.py
from app import app      # importa o Flask já configurado
# from datetime import date # Se você for adicionar datas como data_admissao

def run():
    users_data = [
        dict(
            username="admin",
            email="admin@seudominio.com", # E-mail adicionado
            password_hash=generate_password_hash("Admin123!"),
            role="admin",
            nome_completo="Admin de Souza",
            matricula="ADM001",
            cpf="000.000.000-00", # Exemplo, coloque dados fictícios
            # Novos campos organizacionais como None por enquanto
            estabelecimento_id=None,
            centro_custo_id=None,
            setor_id=None,
            cargo_id=None,
            # Outros campos opcionais
            # data_admissao=date(2020, 1, 15),
            # ramal="1000"
        ),
        dict(
            username="editor",
            email="editor@seudominio.com", # E-mail adicionado
            password_hash=generate_password_hash("Editor123!"),
            role="editor",
            nome_completo="Maria Oliveira",
            matricula="EDT001",
            cpf="111.111.111-11", # Exemplo
            estabelecimento_id=None,
            centro_custo_id=None,
            setor_id=None,
            cargo_id=None,
        ),
        dict(
            username="colaborador",
            email="colaborador@seudominio.com", # E-mail adicionado
            password_hash=generate_password_hash("Colab123!"),
            role="colaborador",
            nome_completo="João Silva",
            matricula="COL001",
            cpf="222.222.222-22", # Exemplo
            estabelecimento_id=None,
            centro_custo_id=None,
            setor_id=None,
            cargo_id=None,
        )
    ]

    with app.app_context(): # Garante o contexto da aplicação Flask
        print("Verificando e criando usuários de exemplo...")
        for user_data in users_data:
            user = User.query.filter_by(username=user_data["username"]).first()
            if not user:
                # Se quiser adicionar outros campos no User, adicione-os ao dict user_data
                # Ex: user_data['ramal'] = "1234"
                # user_data['data_admissao'] = date(2023, 5, 1)
                
                new_user = User(**user_data)
                db.session.add(new_user)
                print(f"Usuário {user_data['username']} criado.")
            else:
                print(f"Usuário {user_data['username']} já existe.")
        
        db.session.commit()
        print("🚀 Seed de usuários concluído.")

if __name__ == "__main__":
    run()