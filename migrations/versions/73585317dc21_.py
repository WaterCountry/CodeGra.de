"""Add cgignore_version field

Revision ID: 73585317dc21
Revises: d069b5a7b4bd
Create Date: 2019-03-27 16:59:24.001832

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '73585317dc21'
down_revision = 'd069b5a7b4bd'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('Assignment', sa.Column('cgignore_version', sa.Unicode(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('Assignment', 'cgignore_version')
    # ### end Alembic commands ###
