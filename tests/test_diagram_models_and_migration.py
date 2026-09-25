"""Regression tests for the diagram persistence contract."""

from pathlib import Path
from uuid import UUID

from sqlalchemy.dialects.postgresql import JSONB

from core.database import db
from core.enums import DiagramScope, DiagramStatus, DiagramType
from core.models import (
    Article, ArticleDiagram, Diagram, DiagramAsset, DiagramVersion, User,
    diagram_share_celula, diagram_share_estabelecimento,
    diagram_share_instituicao, diagram_share_setor, diagram_share_user,
)

MIGRATION = Path('migrations/versions/f2a3b4c5d6e7_add_diagram_tables.py')


def _ondelete(model, column):
    return next(iter(model.__table__.c[column].foreign_keys)).ondelete


def test_diagram_domain_constraints_and_fk_policies(app_ctx):
    assert isinstance(Diagram.__table__.c.scene_data.type.dialect_impl(db.engine.dialect), db.JSON)
    assert isinstance(Diagram.__table__.c.scene_data.type, JSONB)
    assert not Diagram.__table__.c.owner_id.nullable
    assert _ondelete(Diagram, 'owner_id') == 'RESTRICT'
    assert _ondelete(Diagram, 'source_diagram_id') == 'SET NULL'
    assert _ondelete(DiagramVersion, 'diagram_id') == 'CASCADE'
    assert _ondelete(DiagramAsset, 'diagram_id') == 'CASCADE'
    assert _ondelete(ArticleDiagram, 'article_id') == 'CASCADE'
    assert _ondelete(ArticleDiagram, 'diagram_id') == 'RESTRICT'
    assert Article.diagram_links.property.passive_deletes == 'all'

    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in DiagramVersion.__table__.constraints
        if constraint.__class__.__name__ == 'UniqueConstraint'
    }
    assert ('diagram_id', 'version_number') in unique_columns


def test_diagram_defaults_ids_and_relationships(app_ctx):
    owner = User(username='diagram_owner', email='diagram@example.test', password_hash='x')
    source = Diagram(name='Modelo', scene_data={}, owner=owner,
                     diagram_type=DiagramType.TEMPLATE)
    diagram = Diagram(name='Fluxo', scene_data={'nodes': []}, owner=owner,
                      source_diagram=source, scope=DiagramScope.PRIVATE)
    version = DiagramVersion(diagram=diagram, version_number=1, name=diagram.name,
                             scene_data=diagram.scene_data, author=owner)
    asset = DiagramAsset(diagram=diagram, storage_key='diagram/test.svg')
    db.session.add_all([owner, source, diagram, version, asset])
    db.session.commit()

    assert isinstance(diagram.id, UUID)
    assert isinstance(version.id, UUID)
    assert diagram.owner is owner
    assert diagram.source_diagram is source
    assert version in diagram.versions and asset in diagram.assets
    assert diagram.status is DiagramStatus.ACTIVE


def test_all_explicit_sharing_tables_have_composite_primary_keys():
    for table in (
        diagram_share_user, diagram_share_instituicao,
        diagram_share_estabelecimento, diagram_share_setor, diagram_share_celula,
    ):
        assert len(table.primary_key.columns) == 2
        assert 'diagram_id' in table.primary_key.columns


def test_migration_uses_postgresql_types_indexes_and_no_undefined_fts():
    source = MIGRATION.read_text()
    assert 'postgresql.UUID' in source
    assert 'postgresql.JSONB' in source
    for index in (
        'ix_diagram_owner_id', 'ix_diagram_status', 'ix_diagram_type',
        'ix_diagram_scope', 'ix_diagram_updated_at', 'ix_diagram_name',
        'ix_diagram_instituicao_id', 'ix_diagram_estabelecimento_id',
        'ix_diagram_setor_id', 'ix_diagram_celula_id',
    ):
        assert index in source
    # Library search semantics have not been specified, so no premature FTS/GIN.
    assert 'to_tsvector' not in source
    assert "postgresql_using='gin'" not in source
