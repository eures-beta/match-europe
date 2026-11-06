"""Promote an explicitly reviewed staging bundle after offline validation."""

import argparse
import tempfile
from pathlib import Path

from .refresh_catalog import FILES
from .validate_catalog import validate


def promote(source, target):
    source, target = Path(source), Path(target)
    if source.resolve() == target.resolve() or target.is_symlink():
        raise ValueError(
            'Choose distinct staging and target directories, without symlinks'
        )
    report = validate(source)
    # Capture and validate before replacing any versioned file.
    contents = {
        name: (source / name).read_bytes() for name in (*FILES, 'manifest.json')
    }
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as directory:
        temporary = Path(directory)
        for name, raw in contents.items():
            (temporary / name).write_bytes(raw)
        for name in contents:
            (temporary / name).replace(target / name)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--target', type=Path, required=True)
    args = parser.parse_args()
    result = promote(args.source, args.target)
    print(
        f"Promoted {len(FILES)} JSON files and manifest; {len(result['searchChecks'])} multilingual searches passed. Review the Git diff before creating a PR."
    )
