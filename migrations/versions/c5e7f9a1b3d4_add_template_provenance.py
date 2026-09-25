"""add diagram template provenance

Revision ID: c5e7f9a1b3d4
Revises: a4d5e6f7b8c9
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c5e7f9a1b3d4"
down_revision = "a4d5e6f7b8c9"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)

def upgrade():
    op.add_column("diagram", sa.Column("source_template_id", UUID, nullable=True))
    op.create_foreign_key("fk_diagram_source_template_id", "diagram", "diagram",
                          ["source_template_id"], ["id"], ondelete="SET NULL")
    op.add_column("diagram_version", sa.Column("source_version_id", UUID, nullable=True))
    op.create_foreign_key("fk_diagram_version_source_version_id", "diagram_version",
                          "diagram_version", ["source_version_id"], ["id"], ondelete="SET NULL")
    op.execute(sa.text("UPDATE funcao SET codigo = 'diagrama_modelo_gerenciar' "
                       "WHERE codigo = 'diagrama_gerenciar_modelos'"))

def downgrade():
    op.execute(sa.text("UPDATE funcao SET codigo = 'diagrama_gerenciar_modelos' "
                       "WHERE codigo = 'diagrama_modelo_gerenciar'"))
    op.drop_constraint("fk_diagram_version_source_version_id", "diagram_version", type_="foreignkey")
    op.drop_column("diagram_version", "source_version_id")
    op.drop_constraint("fk_diagram_source_template_id", "diagram", type_="foreignkey")
    op.drop_column("diagram", "source_template_id")
