"""Add needed NON NULL constraints

Revision ID: bfa62bee03d2
Revises: 9da3924d4ecc
Create Date: 2020-02-15 00:00:54.923808

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlalchemy_utils

# revision identifiers, used by Alembic.
revision = 'bfa62bee03d2'
down_revision = '9da3924d4ecc'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('Assignment', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False)
    op.alter_column('Assignment', 'name',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('AssignmentLinter', 'Assignment_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('AssignmentLinter', 'name',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('AutoTestRun', 'job_id',
               existing_type=postgresql.UUID(),
               nullable=False)
    op.alter_column('AutoTestRunner', 'last_heartbeat',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False)
    op.alter_column('Comment', 'comment',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('Course', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False)
    op.alter_column('Course_Role', 'name',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('File', 'is_directory',
               existing_type=sa.BOOLEAN(),
               nullable=False)
    op.alter_column('File', 'modification_date',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False)
    op.alter_column('GradeHistory', 'changed_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False)
    op.alter_column('Group', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False)
    op.alter_column('GroupSet', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False)
    op.alter_column('LTIProvider', 'key',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('LinterComment', 'File_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('LinterComment', 'line',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('LinterComment', 'linter_code',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('LinterComment', 'linter_id',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('LinterInstance', 'Work_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('LinterInstance', 'tester_id',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('Permission', 'course_permission',
               existing_type=sa.BOOLEAN(),
               nullable=False)
    op.alter_column('Permission', 'default_value',
               existing_type=sa.BOOLEAN(),
               nullable=False)
    op.alter_column('Permission', 'name',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('PlagiarismCase', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False)
    op.alter_column('PlagiarismRun', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False)
    op.alter_column('Role', 'name',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('RubricItem', 'Rubricrow_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('RubricItem', 'description',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('RubricItem', 'header',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('RubricItem', 'points',
               existing_type=postgresql.DOUBLE_PRECISION(precision=53),
               nullable=False)
    op.alter_column('RubricRow', 'header',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('User', 'active',
               existing_type=sa.BOOLEAN(),
               nullable=False)
    op.alter_column('User', 'name',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('Work', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False)
    op.alter_column('auto_test_output_file', 'auto_test_result_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('auto_test_output_file', 'modification_date',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('auto_test_output_file', 'modification_date',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True)
    op.alter_column('auto_test_output_file', 'auto_test_result_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('Work', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True)
    op.alter_column('User', 'name',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('User', 'active',
               existing_type=sa.BOOLEAN(),
               nullable=True)
    op.alter_column('RubricRow', 'header',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('RubricItem', 'points',
               existing_type=postgresql.DOUBLE_PRECISION(precision=53),
               nullable=True)
    op.alter_column('RubricItem', 'header',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('RubricItem', 'description',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('RubricItem', 'Rubricrow_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('Role', 'name',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('PlagiarismRun', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True)
    op.alter_column('PlagiarismCase', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True)
    op.alter_column('Permission', 'name',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('Permission', 'default_value',
               existing_type=sa.BOOLEAN(),
               nullable=True)
    op.alter_column('Permission', 'course_permission',
               existing_type=sa.BOOLEAN(),
               nullable=True)
    op.alter_column('LinterInstance', 'tester_id',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('LinterInstance', 'Work_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('LinterComment', 'linter_id',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('LinterComment', 'linter_code',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('LinterComment', 'line',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('LinterComment', 'File_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('LTIProvider', 'key',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('GroupSet', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True)
    op.alter_column('Group', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True)
    op.alter_column('GradeHistory', 'changed_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True)
    op.alter_column('File', 'modification_date',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True)
    op.alter_column('File', 'is_directory',
               existing_type=sa.BOOLEAN(),
               nullable=True)
    op.alter_column('Course_Role', 'name',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('Course', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True)
    op.alter_column('Comment', 'comment',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('AutoTestRunner', 'last_heartbeat',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True)
    op.alter_column('AutoTestRun', 'job_id',
               existing_type=postgresql.UUID(),
               nullable=True)
    op.alter_column('AssignmentLinter', 'name',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('AssignmentLinter', 'Assignment_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('Assignment', 'name',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('Assignment', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True)
    # ### end Alembic commands ###
