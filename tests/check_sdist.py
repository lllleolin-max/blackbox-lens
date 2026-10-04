"""Check the actual built source archive; stdlib only, run after python -m build."""
from pathlib import Path
import json
import tarfile


def check_sdist(directory: Path = Path("dist")) -> None:
    archives = list(directory.glob("*.tar.gz"))
    if len(archives) != 1:
        raise AssertionError("expected exactly one built source archive")
    required = {"README.md", "LICENSE", "docs/METHODOLOGY.md", "docs/SELF_REVIEW.md",
                "docs/reviews/RUBRIC.md", "examples/minimal.json", "examples/demo.json",
                "src/blackbox_lens/data/demo.json", "tests/check_sdist.py", "tools/deepseek_batch.py",
                "experiments/deepseek-2026-10-05/suite.json", "experiments/deepseek-2026-10-05/PROTOCOL.md",
                "experiments/deepseek-2026-10-05/ANSWER_KEY.md"}
    with tarfile.open(archives[0], "r:gz") as archive:
        files = {member.name.split("/", 1)[1]: member for member in archive.getmembers()
                 if member.isfile() and "/" in member.name}
        missing = required - files.keys()
        if missing:
            raise AssertionError(f"source archive is missing required files: {sorted(missing)}")
        for name in ("examples/minimal.json", "examples/demo.json"):
            with archive.extractfile(files[name]) as stream:
                fixture = json.load(stream)
            if fixture.get("schema_version") != 1 or not fixture.get("cases"):
                raise AssertionError(f"invalid archived fixture: {name}")
        with archive.extractfile(files["examples/demo.json"]) as stream:
            source_demo = json.load(stream)
        with archive.extractfile(files["src/blackbox_lens/data/demo.json"]) as stream:
            bundled_demo = json.load(stream)
        if source_demo != bundled_demo:
            raise AssertionError("archived source and bundled demos differ")
    print(f"Source archive verified: {archives[0].name}; {len(required)} required files present.")


if __name__ == "__main__":
    check_sdist()
