"""Add sequence for article.id"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_add_article_id_sequence'
down_revision = '0001_oracle_initial'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    max_id = conn.execute(sa.text('SELECT COALESCE(MAX(id), 0) FROM article')).scalar()
    article_id_seq = sa.Sequence('article_id_seq', start=max_id + 1)
    op.execute(sa.schema.CreateSequence(article_id_seq))
    op.execute(sa.text('ALTER TABLE article MODIFY (id DEFAULT article_id_seq.NEXTVAL)'))


def downgrade():
    op.execute(sa.text('ALTER TABLE article MODIFY (id DEFAULT NULL)'))
    op.execute(sa.schema.DropSequence(sa.Sequence('article_id_seq')))
