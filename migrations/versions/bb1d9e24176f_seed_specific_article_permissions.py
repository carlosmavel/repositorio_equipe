"""seed scoped article permissions"""

from alembic import op
import sqlalchemy as sa

revision = 'bb1d9e24176f'
down_revision = 'fa23b0c1c9d0'
branch_labels = None
depends_on = None


PERMS = [
    ("artigo_editar_celula", "Artigo editar celula"),
    ("artigo_editar_setor", "Artigo editar setor"),
    ("artigo_editar_estabelecimento", "Artigo editar estabelecimento"),
    ("artigo_editar_instituicao", "Artigo editar instituicao"),
    ("artigo_editar_todas", "Artigo editar todas"),
    ("artigo_aprovar_celula", "Artigo aprovar celula"),
    ("artigo_aprovar_setor", "Artigo aprovar setor"),
    ("artigo_aprovar_estabelecimento", "Artigo aprovar estabelecimento"),
    ("artigo_aprovar_instituicao", "Artigo aprovar instituicao"),
    ("artigo_aprovar_todas", "Artigo aprovar todas"),
    ("artigo_revisar_celula", "Artigo revisar celula"),
    ("artigo_revisar_setor", "Artigo revisar setor"),
    ("artigo_revisar_estabelecimento", "Artigo revisar estabelecimento"),
    ("artigo_revisar_instituicao", "Artigo revisar instituicao"),
    ("artigo_revisar_todas", "Artigo revisar todas"),
    ("artigo_assumir_revisao_celula", "Artigo assumir revisao celula"),
    ("artigo_assumir_revisao_setor", "Artigo assumir revisao setor"),
    ("artigo_assumir_revisao_estabelecimento", "Artigo assumir revisao estabelecimento"),
    ("artigo_assumir_revisao_instituicao", "Artigo assumir revisao instituicao"),
    ("artigo_assumir_revisao_todas", "Artigo assumir revisao todas"),
    ("artigo_tipo_gerenciar", "Artigo tipo gerenciar"),
    ("artigo_area_gerenciar", "Artigo area gerenciar"),
    ("artigo_ocr_reprocessar", "Artigo ocr reprocessar"),
    ("artigo_excluir_definitivo", "Artigo excluir definitivo"),
]


def upgrade():
    connection = op.get_bind()
    for codigo, nome in PERMS:
        res = connection.execute(
            sa.text("SELECT id FROM funcao WHERE codigo=:c"), {"c": codigo}
        ).first()
        if not res:
            connection.execute(
                sa.text("INSERT INTO funcao (codigo, nome) VALUES (:c, :n)"),
                {"c": codigo, "n": nome},
            )


def downgrade():
    connection = op.get_bind()
    codes = [codigo for codigo, _nome in PERMS]
    connection.execute(
        sa.text("DELETE FROM funcao WHERE codigo = ANY(:codes)"),
        {"codes": codes},
    )
