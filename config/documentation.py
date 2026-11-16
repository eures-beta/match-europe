"""Bound shared instruction context without loading Django or contacting services."""

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Budget:
    bytes: int
    lines: int


REQUIRED = {
    'AGENTS.md': Budget(10 * 1024, 180),
    'HANDOFF.md': Budget(6 * 1024, 100),
    'docs/DECISIONS.md': Budget(10 * 1024, 160),
    'docs/VUE_ENSEMBLE.md': Budget(6 * 1024, 100),
    'docs/AGENT_FEEDBACK.md': Budget(8 * 1024, 140),
    'docs/AGENT_WORKFLOW.md': Budget(8 * 1024, 140),
    'docs/DOCUMENTATION.md': Budget(8 * 1024, 140),
}
NESTED = Budget(4 * 1024, 80)
SKILL = Budget(4 * 1024, 90)
CHAIN_BYTES = 20 * 1024
IGNORED = {'.git', 'node_modules', '__pycache__', '.runtime', 'staticfiles', 'build'}
INSTRUCTIONS = {'AGENTS.md', 'AGENTS.override.md'}


def instruction_files(root):
    """Include new subtree rules/skills, but not installed or generated resources."""
    for directory, folders, files in os.walk(root, followlinks=False):
        folders[:] = sorted(
            name
            for name in folders
            if name not in IGNORED and not name.startswith('.venv')
        )
        for name in sorted(files):
            if name in INSTRUCTIONS or name == 'SKILL.md':
                yield Path(directory) / name


def check_documents(root, required=None):
    root = Path(root)
    required = REQUIRED if required is None else required
    limits = {root / name: budget for name, budget in required.items()}
    for path in instruction_files(root):
        limits.setdefault(path, SKILL if path.name == 'SKILL.md' else NESTED)
    errors, measurements, instruction_sizes = [], [], {}
    for path, budget in sorted(limits.items()):
        relative = path.relative_to(root).as_posix()
        try:
            content = path.read_bytes()
            lines = len(content.decode('utf-8').splitlines())
        except (OSError, UnicodeError):
            errors.append(f'{relative}: fichier requis absent ou illisible en UTF-8')
            continue
        size = len(content)
        measurements.append(
            f'{relative}: {size}/{budget.bytes} octets, {lines}/{budget.lines} lignes'
        )
        if size > budget.bytes or lines > budget.lines:
            errors.append(measurements[-1] + ' — budget dépassé')
        if path.name in INSTRUCTIONS:
            instruction_sizes[path] = size
    # Count overrides conservatively as well: do not depend on a client's loader.
    for directory in sorted({path.parent for path in instruction_sizes}):
        total = sum(
            size
            for path, size in instruction_sizes.items()
            if path.parent == directory or path.parent in directory.parents
        )
        if total > CHAIN_BYTES:
            relative = directory.relative_to(root).as_posix()
            errors.append(
                f'{relative}: chaîne AGENTS {total}/{CHAIN_BYTES} octets — budget dépassé'
            )
    return errors, measurements


def main():
    errors, measurements = check_documents(Path(__file__).resolve().parents[1])
    for line in measurements:
        print(line)
    for error in errors:
        print('ERREUR : ' + error)
    if errors:
        print(
            'Actualiser ou scinder les documents ; Git conserve les anciennes versions.'
        )
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
