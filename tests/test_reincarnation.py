from kmac_agent_friend.config import Settings
from kmac_agent_friend.knowledge.ingest import KNOWLEDGE_COLLECTION
from kmac_agent_friend.memory.history import ConversationStore
from kmac_agent_friend.memory.vector_store import LongTermMemory
from kmac_agent_friend.reincarnation import export_bundle, import_bundle
from kmac_agent_friend.settings_store import load_user_overrides, save_user_overrides


def _seed(settings: Settings) -> None:
    store = ConversationStore.from_settings(settings)
    store.append("user", "remember my name is Sam")
    store.append("assistant", "Got it, Sam.")

    mem = LongTermMemory(settings.kaf_data_dir / "memory" / "longterm.db", collection="memories")
    mem.add("Sam likes espresso", [1.0, 0.0, 0.0], metadata={"source": "chat"})

    kb = LongTermMemory(
        settings.kaf_data_dir / "memory" / "longterm.db", collection=KNOWLEDGE_COLLECTION
    )
    kb.add("Espresso is brewed under pressure", [0.5, 0.5, 0.0], metadata={"domain": "coffee"})

    save_user_overrides(settings.kaf_data_dir, {"ollama_model": "mistral"})


def test_export_then_import_roundtrip(tmp_path):
    src = Settings(kaf_data_dir=tmp_path / "src")
    _seed(src)
    bundle = export_bundle(src)

    assert bundle["version"] == 1
    assert len(bundle["memories"]) == 1
    assert len(bundle["knowledge"]) == 1
    assert any(c["messages"] for c in bundle["conversations"])
    assert bundle["settings"]["ollama_model"] == "mistral"

    dst = Settings(kaf_data_dir=tmp_path / "dst")
    report = import_bundle(dst, bundle)

    assert report.ok
    assert report.memories == 1
    assert report.knowledge == 1
    assert report.messages >= 2
    assert report.settings_applied

    dst_mem = LongTermMemory(
        dst.kaf_data_dir / "memory" / "longterm.db", collection="memories"
    )
    assert dst_mem.count() == 1
    assert load_user_overrides(dst.kaf_data_dir)["ollama_model"] == "mistral"


def test_import_rejects_non_dict(tmp_path):
    dst = Settings(kaf_data_dir=tmp_path)
    report = import_bundle(dst, [])  # type: ignore[arg-type]
    assert not report.ok
