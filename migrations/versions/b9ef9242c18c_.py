"""Update enums and add after_run_called column

Revision ID: b9ef9242c18c
Revises: 1dd5be4da723
Create Date: 2019-05-22 15:56:53.228639

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b9ef9242c18c'
down_revision = '1dd5be4da723'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('AutoTestResult', 'points_achieved')
    op.add_column('AutoTestRunner', sa.Column('after_run_called', sa.Boolean(), server_default='true', nullable=False))
    op.sync_enum_values('public', 'autoteststepresultstate', ['failed', 'not_started', 'passed', 'running'], ['failed', 'not_started', 'passed', 'running', 'timed_out'])
    op.sync_enum_values('public', 'autotestrunstate', ['not_started', 'running', 'done', 'timed_out'], ['not_started', 'running', 'done', 'timed_out','crashed'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.sync_enum_values('public', 'autoteststepresultstate', ['failed', 'not_started', 'passed', 'running', 'timed_out'], ['failed', 'not_started', 'passed', 'running'])
    op.sync_enum_values('public', 'autotestrunstate', ['not_started', 'running', 'done', 'timed_out','crashed'], ['not_started', 'running', 'done', 'timed_out'])
    op.drop_column('AutoTestRunner', 'after_run_called')
    op.add_column('AutoTestResult', sa.Column('points_achieved', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    # ### end Alembic commands ###