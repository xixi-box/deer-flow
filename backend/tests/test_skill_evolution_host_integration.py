"""Real SQLite, host assembly, evidence, projection and public-only consumer."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
from deerflow_extension_api import ExtensionData, ExtensionRuntimeDeps, HostPolicySnapshot
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from deerflow.config.database_config import DatabaseConfig
from deerflow.config.paths import Paths
from deerflow.extensions.host_capabilities import HostCapabilities
from deerflow.extensions.loader import ExtensionSpec
from deerflow.persistence.base import Base
from deerflow.persistence.run import RunRepository
from deerflow.persistence.run.model import RunRow
from deerflow.persistence.user.model import UserRow
from deerflow.runtime.events.store.db import DbRunEventStore
from deerflow.skills.mutations.scanner import CandidateScanner, ScanVerdict
from deerflow.skills.storage.user_scoped_skill_storage import UserScopedSkillStorage


@pytest.mark.asyncio
async def test_public_consumer_end_to_end_and_plugin_removed_restart(tmp_path, monkeypatch):
    monkeypatch.setattr("deerflow.config.paths._paths", Paths(base_dir=tmp_path / "home"))
    storage = UserScopedSkillStorage("owner", host_path=str(tmp_path / "skills"))
    root = storage.get_custom_skill_dir("example")
    root.mkdir(parents=True)
    content = "---\nname: example\ndescription: A sample skill\n---\nOriginal body.\n"
    (root / "SKILL.md").write_text(content, encoding="utf-8")
    database = DatabaseConfig(backend="sqlite", sqlite_dir=str(tmp_path))
    engine = create_engine(database.app_sync_sqlalchemy_url)
    Base.metadata.create_all(engine)
    engine.dispose()
    async_engine = create_async_engine(database.app_sqlalchemy_url)
    sf = async_sessionmaker(async_engine, expire_on_commit=False)
    async with sf.begin() as session:
        session.add(UserRow(id="owner", email="owner@example.test"))
        session.add(RunRow(run_id="run", thread_id="thread", user_id="owner", status="success", evidence_seal_state="sealed", evidence_agent_id="lead_agent", evidence_origin="interactive", evidence_upper_seq=0, evidence_event_count=0))

    async def scan(self, package, name):
        assert name == "example"
        assert package.main_content.startswith("---")
        return ScanVerdict("allow", "CHECK_PASSED", "test-policy")

    async def policy(self):
        return "test-policy"

    monkeypatch.setattr(CandidateScanner, "scan", scan)
    monkeypatch.setattr(CandidateScanner, "policy_version", policy)
    monkeypatch.setattr(CandidateScanner, "policy_version_sync", lambda _: "test-policy")
    spec = ExtensionSpec(
        use="fixture:install",
        name="fixture",
        host_access={
            "evidence": {"owners": ["owner"]},
            "skill_mutations": {"owners": ["owner"], "operations": ["stage", "check", "commit", "revert"], "trigger_agents": ["lead_agent"], "target_skills": ["example"], "topology": "single_host_local"},
        },
    )
    config = SimpleNamespace(database=database, plugins=[spec])
    host = HostCapabilities(config, RunRepository(sf), DbRunEventStore(sf), root=tmp_path, storage_factory=lambda _: storage)
    try:
        await host.start()
        evidence, mutations = host.bindings[spec.use]
        deps = ExtensionRuntimeDeps(app_store=ExtensionData("fixture"), policy=HostPolicySnapshot(), completed_run_evidence=evidence, skill_mutations=mutations)
        module_spec = importlib.util.spec_from_file_location("external_consumer", Path(__file__).parent / "fixtures" / "skill_evolution_consumer.py")
        consumer = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(consumer)
        operation, reverted = await consumer.exercise(deps, thread_id="thread", run_id="run", name="example")
        assert (operation.views, reverted.views) == ("READY", "READY")
        assert (root / "SKILL.md").read_text(encoding="utf-8") == content
        await host.close()
        config.plugins = []
        host = HostCapabilities(config, RunRepository(sf), DbRunEventStore(sf), root=tmp_path, storage_factory=lambda _: storage)
        await host.start()
        assert host.bindings == {}
        assert "owner" in host.runtime.owners
        assert host.recovery.get_operation(reverted.operation_id).publication == "APPLIED"
    finally:
        await host.close()
        await async_engine.dispose()


@pytest.mark.asyncio
async def test_completed_tool_heavy_chat_stages_skill_revision(tmp_path, monkeypatch):
    import asyncio
    import json
    from unittest.mock import AsyncMock

    from langchain.agents import create_agent
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
    from langchain_core.messages import AIMessage, HumanMessage
    from langchain_core.tools import tool

    from deerflow.config.run_ownership_config import RunOwnershipConfig
    from deerflow.extensions.gateway import start_services, stop_services
    from deerflow.extensions.loader import load_extensions
    from deerflow.runtime.runs.manager import RunManager, RunStatus
    from deerflow.runtime.runs.worker import RunContext, run_agent
    from deerflow.runtime.stream_bridge import MemoryStreamBridge

    example = Path(__file__).resolve().parents[2] / "examples/deerflow-extension-skill-evolution"
    monkeypatch.syspath_prepend(str(example))
    monkeypatch.setattr("deerflow.config.paths._paths", Paths(base_dir=tmp_path / "home"))
    storage = UserScopedSkillStorage("owner", host_path=str(tmp_path / "skills"))
    root = storage.get_custom_skill_dir("example-skill")
    root.mkdir(parents=True)
    baseline = "---\nname: example-skill\ndescription: A sample skill\n---\nRun the converter with --fmt json.\n"
    candidate = baseline.replace("--fmt json", "--format json")
    (root / "SKILL.md").write_text(baseline, encoding="utf-8")

    database = DatabaseConfig(backend="sqlite", sqlite_dir=str(tmp_path))
    engine = create_async_engine(database.app_sqlalchemy_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sf = async_sessionmaker(engine, expire_on_commit=False)
    async with sf.begin() as session:
        session.add(UserRow(id="owner", email="owner@example.test"))

    spec = ExtensionSpec(
        name="skill-evolution",
        use="deerflow_extension_skill_evolution:install",
        host_access={
            "evidence": {"owners": ["owner"]},
            "model_invocation": {"roles": {"review": "review-model"}},
            "skill_mutations": {"owners": ["owner"], "operations": ["stage"], "target_skills": ["example-skill"], "trigger_agents": ["lead_agent"], "topology": "single_host_local"},
        },
        config={"background_review": {"target_skill": "example-skill", "creation_nudge_interval": 2, "model_role": "review"}},
    )
    model_started, release_model = asyncio.Event(), asyncio.Event()

    async def review(messages, **kwargs):
        model_started.set()
        await release_model.wait()
        return AIMessage(content=json.dumps({"candidate_content": candidate}))

    model = SimpleNamespace(ainvoke=AsyncMock(side_effect=review))
    monkeypatch.setattr("deerflow.extensions.model_invocation.create_chat_model", lambda *args, **kwargs: model)
    config = SimpleNamespace(database=database, plugins=[spec], get_model_config=lambda name: object() if name == "review-model" else None)
    runs, events = RunRepository(sf), DbRunEventStore(sf)
    host = HostCapabilities(config, runs, events, root=tmp_path, storage_factory=lambda owner: storage)
    extensions, diagnostics = load_extensions([spec])
    assert not diagnostics

    class LeadModel(GenericFakeChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    @tool
    async def convert(options: str) -> str:
        """Convert a sample document."""
        return "converted" if options == "--format json" else "unknown option"

    responses = [AIMessage(content="", tool_calls=[{"name": "convert", "args": {"options": options}, "id": f"convert-{index}"}]) for index, options in enumerate(("--fmt json", "--format json"))]
    lead_agent = create_agent(LeadModel(messages=iter([*responses, "Done"]), disable_streaming=True), tools=[convert])

    try:
        await host.start()
        assert not await start_services(extensions, config, sf, host_capabilities=host.bindings)
        manager = RunManager(store=runs, event_store=events, worker_id="worker", run_ownership_config=RunOwnershipConfig(heartbeat_enabled=True, lease_seconds=300))
        record = await manager.create_or_reject("thread", user_id="owner", evidence_origin="interactive", evidence_agent_id="lead_agent")
        worker = asyncio.create_task(
            run_agent(
                MemoryStreamBridge(),
                manager,
                record,
                ctx=RunContext(checkpointer=None, extensions=extensions, event_store=events),
                agent_factory=lambda **kwargs: lead_agent,
                graph_input={"messages": [HumanMessage(content="Convert this document to JSON.")]},
                config={"configurable": {"thread_id": record.thread_id}},
            )
        )
        record.task = worker
        await asyncio.wait_for(worker, 10)
        assert record.status is RunStatus.success
        evidence, mutations = host.bindings[spec.use]
        snapshot = await evidence.get_snapshot(thread_id=record.thread_id, run_id=record.run_id)
        assert snapshot.seal_state == "sealed"

        # The foreground finished even though the provider cannot return yet.
        try:
            await asyncio.wait_for(model_started.wait(), 5)
        except TimeoutError:
            pass
        assert model.ainvoke.await_count == 1, "completed tool-heavy chat did not trigger background skill review"
        messages = model.ainvoke.call_args.args[0]
        assert all("unknown option" not in message.content and "--fmt json" not in message.content for message in messages if message.type == "system")
        data = json.loads(next(message.content for message in messages if message.type == "human" and "existing_skill" in message.content))
        assert data["existing_skill"] == baseline
        assert data["conversation_excerpts"] == [
            {"role": "human", "text": "Convert this document to JSON."},
            {"role": "tool (convert)", "text": "unknown option"},
            {"role": "tool (convert)", "text": "converted"},
            {"role": "ai", "text": "Done"},
        ]
        release_model.set()

        evolution = extensions.services[0][1].service
        async with asyncio.timeout(10):
            while not evolution.list_proposals():
                await asyncio.sleep(0.01)
        [proposal] = evolution.list_proposals()
        assert (proposal.owner_id, proposal.name, proposal.decision) == ("owner", "example-skill", "justified")
        staged = await mutations.get_proposal(proposal_id=proposal.proposal_id)
        assert staged.source_refs == (snapshot.snapshot_ref,)
        bundle = await mutations.read_proposal_bundle(proposal_id=proposal.proposal_id)
        assert {item.path: item.content.decode() for item in bundle.candidate} == {"SKILL.md": candidate}
        assert (root / "SKILL.md").read_text(encoding="utf-8") == baseline
    finally:
        release_model.set()
        await stop_services(extensions)
        await host.close()
        await engine.dispose()
