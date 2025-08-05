import glob

def _get_heads():
    revisions = set()
    downs = set()
    for path in glob.glob("migrations/versions/*.py"):
        revision = None
        down_values = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("revision ="):
                    revision = line.split("=", 1)[1].strip().strip("'\"")
                elif line.startswith("down_revision"):
                    raw = line.split("=", 1)[1].strip()
                    if raw.startswith("("):
                        down_values = [
                            part.strip().strip("'\"")
                            for part in raw.strip("()").split(",")
                            if part.strip()
                        ]
                    elif raw in {"None", "NULL"}:
                        down_values = []
                    else:
                        down_values = [raw.strip("'\"")]
        if revision:
            revisions.add(revision)
        downs.update(down_values)
    return revisions - downs

def test_single_alembic_head():
    heads = _get_heads()
    assert len(heads) == 1, f"multiple migration heads detected: {heads}"
