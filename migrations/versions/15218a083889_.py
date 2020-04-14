"""Make usernames case insensitive

Revision ID: 15218a083889
Revises: 600c026809b0
Create Date: 2020-04-14 14:50:10.933284

"""
import sqlalchemy as sa
import sqlalchemy_utils
from citext import CIText
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '15218a083889'
down_revision = '600c026809b0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        'User',
        'username',
        existing_type=sa.VARCHAR(),
        type_=CIText(),
        existing_nullable=False
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        'User',
        'username',
        existing_type=CIText(),
        type_=sa.VARCHAR(),
        existing_nullable=False
    )
    # ### end Alembic commands ###
