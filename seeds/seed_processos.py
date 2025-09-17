try:
    from .core.database import db
except ImportError:
    from core.database import db

try:
    from .core.models import Processo, ProcessoEtapa, CampoEtapa, Cargo
except ImportError:
    from core.models import Processo, ProcessoEtapa, CampoEtapa, Cargo

try:
    from .seed_demonstration import get_or_create
except ImportError:  # pragma: no cover - fallback for direct execution
    from seed_demonstration import get_or_create

from app import app


def run():
    with app.app_context():
        if Processo.query.filter_by(nome="Onboarding de Novo Colaborador").first():
            print("Processo de onboarding já existe.")
            return

        processo = Processo(
            nome="Onboarding de Novo Colaborador",
            descricao="Fluxo básico de integração",
        )
        db.session.add(processo)
        db.session.flush()

        # obtém um cargo existente ou cria um genérico com id manual
        cargo = Cargo.query.first()
        if not cargo:
            cargo = get_or_create(Cargo, nome="Cargo Padrão", defaults={"ativo": True})
            db.session.flush()

        etapa_rh = ProcessoEtapa(nome="RH - Cadastro", ordem=1, processo=processo)
        etapa_ti = ProcessoEtapa(nome="TI - Acesso", ordem=2, processo=processo)
        etapa_gestor = ProcessoEtapa(
            nome="Gestor - Boas-vindas", ordem=3, processo=processo
        )

        db.session.add_all([etapa_rh, etapa_ti, etapa_gestor])

        etapa_rh.cargos_que_atendem.append(cargo)
        etapa_ti.cargos_que_atendem.append(cargo)
        etapa_gestor.cargos_que_atendem.append(cargo)

        campos = [
            CampoEtapa(etapa=etapa_rh, nome="Documentos", tipo="checkbox", obrigatorio=True),
            CampoEtapa(etapa=etapa_ti, nome="Criar usuário", tipo="text", obrigatorio=True),
            CampoEtapa(etapa=etapa_gestor, nome="Mensagem", tipo="textarea", obrigatorio=False),
        ]
        db.session.add_all(campos)

        db.session.commit()
        print("Processo de onboarding criado.")


if __name__ == "__main__":
    run()
