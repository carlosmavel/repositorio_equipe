try:
    from .database import db
except ImportError:
    from database import db

try:
    from .models import Processo, EtapaProcesso, CampoEtapa, Cargo, Setor
except ImportError:
    from models import Processo, EtapaProcesso, CampoEtapa, Cargo, Setor

from app import app


def run():
    with app.app_context():
        if Processo.query.filter_by(nome="Onboarding de Novo Colaborador").first():
            print("Processo de onboarding já existe.")
            return

        processo = Processo(nome="Onboarding de Novo Colaborador", descricao="Fluxo básico de integração")
        db.session.add(processo)
        db.session.flush()

        # assume que existam cargos e setores com ids 1 para exemplo
        etapa_rh = EtapaProcesso(nome="RH - Cadastro", ordem=1, processo=processo, cargo_id=1, obrigatoria=True)
        etapa_ti = EtapaProcesso(nome="TI - Acesso", ordem=2, processo=processo, cargo_id=1, obrigatoria=True)
        etapa_gestor = EtapaProcesso(nome="Gestor - Boas-vindas", ordem=3, processo=processo, cargo_id=1, obrigatoria=True)

        db.session.add_all([etapa_rh, etapa_ti, etapa_gestor])
        db.session.flush()

        CampoEtapa(etapa=etapa_rh, nome="Documentos", tipo="checkbox", obrigatorio=True)
        CampoEtapa(etapa=etapa_ti, nome="Criar usuário", tipo="text", obrigatorio=True)
        CampoEtapa(etapa=etapa_gestor, nome="Mensagem", tipo="textarea", obrigatorio=False)

        db.session.commit()
        print("Processo de onboarding criado.")


if __name__ == "__main__":
    run()
