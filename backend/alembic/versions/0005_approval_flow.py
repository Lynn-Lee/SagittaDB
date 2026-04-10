"""多级审批流：新增 approval_flow / approval_flow_node 表，sql_workflow 加 flow_id 列

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-08
"""
import sqlalchemy as sa

from alembic import op

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 审批流模板主表 ──────────────────────────────────────────
    op.create_table(
        'approval_flow',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.Integer(), nullable=False, default=1, server_default='1'),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=False, server_default=''),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.String(30), nullable=False, server_default=''),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['created_by_id'], ['sql_users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_approval_flow_tenant', 'approval_flow', ['tenant_id'])
    op.create_index('ix_approval_flow_active', 'approval_flow', ['is_active'])

    # ── 审批流节点表 ───────────────────────────────────────────
    op.create_table(
        'approval_flow_node',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.Integer(), nullable=False, default=1, server_default='1'),
        sa.Column('flow_id', sa.Integer(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('node_name', sa.String(100), nullable=False),
        sa.Column('approver_type', sa.String(20), nullable=False, server_default='any_reviewer'),
        sa.Column('approver_ids', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['flow_id'], ['approval_flow.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('flow_id', 'order', name='uq_flow_node_order'),
    )
    op.create_index('ix_approval_flow_node_flow', 'approval_flow_node', ['flow_id'])

    # ── sql_workflow 加 flow_id 外键列 ─────────────────────────
    op.add_column(
        'sql_workflow',
        sa.Column('flow_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_workflow_flow_id',
        'sql_workflow', 'approval_flow',
        ['flow_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_workflow_flow_id', 'sql_workflow', ['flow_id'])


def downgrade() -> None:
    op.drop_index('ix_workflow_flow_id', 'sql_workflow')
    op.drop_constraint('fk_workflow_flow_id', 'sql_workflow', type_='foreignkey')
    op.drop_column('sql_workflow', 'flow_id')

    op.drop_index('ix_approval_flow_node_flow', 'approval_flow_node')
    op.drop_table('approval_flow_node')

    op.drop_index('ix_approval_flow_active', 'approval_flow')
    op.drop_index('ix_approval_flow_tenant', 'approval_flow')
    op.drop_table('approval_flow')
