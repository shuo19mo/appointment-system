from pathlib import Path


def test_production_chat_path_has_no_rule_fallback():
    forbidden = (
        "SCHEDULING_TERMS",
        "CONSULTATION_TERMS",
        "_parse_relative_time",
        "SchedulingInputParser()",
    )
    paths = [Path("agents/task_classification_agent.py"), Path("agents/scheduling/input_parser.py")]
    source = "\n".join(path.read_text() for path in paths)

    assert not any(term in source for term in forbidden)
