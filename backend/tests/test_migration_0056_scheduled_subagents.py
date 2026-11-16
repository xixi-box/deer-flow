"""The opt-in switch preserves legacy tasks across upgrades and rollback."""

import asyncio
import os
import uuid

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy.ext.asyncio import create_async_engine
from support.postgres import asyncpg_test_url

from deerflow.persistence import bootstrap
from deerflow.persistence.postgres_schema import build_asyncpg_connect_args

REVISION = "0056_scheduled_subagents"
PREVIOUS = "0055_thread_shares"
COLUMN = "subagent_enabled"


def test_subagent_revision_is_in_single_chain_after_0055():
    script = ScriptDirectory(str(bootstrap._MIGRATIONS_DIR))
    assert len(script.get_heads()) == 1
    assert REVISION in {revision.revision for revision in script.walk_revisions()}
    assert script.get_heads() == [REVISION]
    assert script.get_revision(REVISION).down_revision == PREVIOUS
    assert len(REVISION) <= 32


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", ["sqlite", "postgres"])
async def test_subagent_migration_preserves_legacy_rows_and_retries(tmp_path, backend):
    schema = None
    if backend == "sqlite":
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'migration.db'}")
    else:
        uri = os.environ.get("TEST_POSTGRES_URI")
        if not uri:
            pytest.skip("requires TEST_POSTGRES_URI (real Postgres migration)")
        schema = f"subagent_switch_{uuid.uuid4().hex}"
        engine = create_async_engine(asyncpg_test_url(uri), connect_args=build_asyncpg_connect_args(schema))
    cfg = bootstrap._get_alembic_config(engine, postgres_schema=schema or "")
    try:
        if schema:
            async with engine.begin() as conn:
                await conn.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
        await asyncio.to_thread(command.upgrade, cfg, PREVIOUS)
        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    "INSERT INTO scheduled_tasks (id,user_id,context_mode,title,prompt,schedule_type,schedule_spec,timezone,status,overlap_policy,run_count,last_occurrence_seq,goal_objective,created_at,updated_at) "
                    "VALUES ('existing','owner','fresh_thread_per_run','Report','Write report','cron','{}','UTC','paused','enqueue',4,4,'report ready',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
                )
            )
        await asyncio.to_thread(command.upgrade, cfg, REVISION)
        async with engine.begin() as conn:
            columns = await conn.run_sync(lambda sync: {col["name"]: col for col in sa.inspect(sync).get_columns("scheduled_tasks")})
            assert columns[COLUMN]["nullable"] and columns[COLUMN]["default"] is None
            foreign_keys = await conn.run_sync(lambda sync: sa.inspect(sync).get_foreign_keys("scheduled_tasks"))
            assert all(COLUMN not in fk["constrained_columns"] for fk in foreign_keys)
            row = (await conn.execute(sa.text(f"SELECT run_count,goal_objective,{COLUMN} FROM scheduled_tasks WHERE id='existing'"))).one()
            assert tuple(row) == (4, "report ready", None)
            await conn.execute(sa.text(f"UPDATE scheduled_tasks SET {COLUMN}=true WHERE id='existing'"))

        from sqlalchemy.ext.asyncio import async_sessionmaker

        from deerflow.persistence.scheduled_tasks import ScheduledTaskRepository

        repo = ScheduledTaskRepository(async_sessionmaker(engine, expire_on_commit=False))
        assert (await repo.get("existing", user_id="owner"))["subagent_enabled"] is True
        await repo.update("existing", user_id="owner", updates={"subagent_enabled": None})
        assert (await repo.get("existing", user_id="owner"))["subagent_enabled"] is False
        await repo.update("existing", user_id="owner", updates={"subagent_enabled": True})

        # Retry upgrade over an already-added column without changing its value.
        await asyncio.to_thread(command.stamp, cfg, PREVIOUS)
        await asyncio.to_thread(command.upgrade, cfg, REVISION)
        async with engine.connect() as conn:
            assert (await conn.execute(sa.text(f"SELECT {COLUMN} FROM scheduled_tasks WHERE id='existing'"))).scalar_one() == 1

        await asyncio.to_thread(command.downgrade, cfg, PREVIOUS)
        async with engine.connect() as conn:
            names = await conn.run_sync(lambda sync: {col["name"] for col in sa.inspect(sync).get_columns("scheduled_tasks")})
            assert COLUMN not in names
            assert (await conn.execute(sa.text("SELECT run_count,goal_objective FROM scheduled_tasks WHERE id='existing'"))).one() == (4, "report ready")
        # Retry downgrade after the column is gone, then upgrade once more.
        await asyncio.to_thread(command.stamp, cfg, REVISION)
        await asyncio.to_thread(command.downgrade, cfg, PREVIOUS)
        await asyncio.to_thread(command.upgrade, cfg, REVISION)
        async with engine.connect() as conn:
            assert (await conn.execute(sa.text(f"SELECT {COLUMN} FROM scheduled_tasks WHERE id='existing'"))).scalar_one() is None
    finally:
        if schema:
            async with engine.begin() as conn:
                await conn.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()
