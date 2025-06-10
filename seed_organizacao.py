from database import db
from models import Instituicao, Estabelecimento, Setor, Celula
from app import app


def run():
    with app.app_context():
        print("Verificando e criando dados de organização...")

        inst = Instituicao.query.filter_by(nome="Instituição Exemplo").first()
        if not inst:
            inst = Instituicao(nome="Instituição Exemplo", descricao="Instituição para testes")
            db.session.add(inst)
            print("Instituição criada.")
        else:
            print("Instituição já existe.")

        est = Estabelecimento.query.filter_by(codigo="EST1").first()
        if not est:
            est = Estabelecimento(codigo="EST1", nome_fantasia="Estabelecimento Exemplo", instituicao=inst)
            db.session.add(est)
            print("Estabelecimento criado.")
        else:
            print("Estabelecimento já existe.")

        setor = Setor.query.filter_by(nome="Setor Exemplo").first()
        if not setor:
            setor = Setor(nome="Setor Exemplo", descricao="Setor para testes", estabelecimento=est)
            db.session.add(setor)
            print("Setor criado.")
        else:
            print("Setor já existe.")

        celula = Celula.query.filter_by(nome="Célula Exemplo").first()
        if not celula:
            celula = Celula(nome="Célula Exemplo", estabelecimento=est, setor=setor)
            db.session.add(celula)
            print("Célula criada.")
        else:
            print("Célula já existe.")

        db.session.commit()
        print("🚀 Seed de organização concluído.")


if __name__ == "__main__":
    run()
