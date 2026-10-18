"""Add missing Yazi shortcuts while preserving user mappings and TOML formatting."""
from dataclasses import dataclass, field
import json
import re
import sys
import tomllib

START = '# >>> Yazi Setup keybindings >>>'
END = '# <<< Yazi Setup keybindings <<<'
OLD_START = '# >>> Yazi Windows Scripts keybindings >>>'
OLD_END = '# <<< Yazi Windows Scripts keybindings <<<'


@dataclass
class MergePlan:
    content: str
    added: list = field(default_factory=list)
    conflicts: list = field(default_factory=list)
    unchanged: list = field(default_factory=list)


def keys(entry):
    value = entry['on']
    return tuple(value) if isinstance(value, list) else (value,)


def active(entry, platform):
    scope = entry.get('for')
    return scope is None or scope == platform or scope == 'unix' and platform == 'linux'


def commands(entry):
    run = entry['run']
    return tuple(run) if isinstance(run, list) else (run,)


def inline(entry):
    return '{ ' + ', '.join(name + ' = ' + json.dumps(value, ensure_ascii=False)
                            for name, value in entry.items()) + ' }'


def table(entry):
    return '[[mgr.prepend_keymap]]\n' + ''.join(
        name + ' = ' + json.dumps(value, ensure_ascii=False) + '\n' for name, value in entry.items())


def plan_merge(existing, proposed, platform):
    for start, end in [(START, END), (OLD_START, OLD_END)]:
        if existing.count(start) != existing.count(end) or (start in existing and existing.index(start) > existing.index(end)):
            raise ValueError('Incomplete managed keymap markers; repair keymap.toml before merging.')
    parsed = tomllib.loads(existing)
    incoming = tomllib.loads(proposed).get('mgr', {}).get('prepend_keymap', [])
    current = [entry for layer in ('prepend_keymap', 'keymap', 'append_keymap')
               for entry in parsed.get('mgr', {}).get(layer, []) if active(entry, platform)]
    result = MergePlan(existing)
    for entry in incoming:
        if not active(entry, platform):
            continue
        wanted = keys(entry)
        occupied = [old for old in current if keys(old) == wanted or
                    keys(old)[:len(wanted)] == wanted or wanted[:len(keys(old))] == keys(old)]
        if occupied:
            if any(keys(old) == wanted and commands(old) == commands(entry) for old in occupied) and all(keys(old) == wanted and commands(old) == commands(entry) for old in occupied):
                result.unchanged.append(entry)
            else:
                result.conflicts.append({'keys': list(wanted), 'requested': entry['run'],
                                         'existing': [{'keys': list(keys(old)), 'run': old['run']} for old in occupied]})
            continue
        result.added.append(entry)
        current.append(entry)
    if not result.added:
        return result

    # Array-of-tables form can always be extended without rewriting user entries.
    addition = '\n# Added by Yazi Setup: previously unmapped shortcuts only\n\n' + '\n'.join(table(entry) for entry in result.added)
    candidate = existing.rstrip() + '\n' + addition if existing.strip() else proposed
    expected = tomllib.loads(proposed) if not existing.strip() else tomllib.loads(existing)
    if existing.strip():
        target = expected.setdefault('mgr', {}).setdefault('prepend_keymap', [])
        target.extend(result.added)
    try:
        if tomllib.loads(candidate) == expected:
            result.content = candidate
            return result
    except tomllib.TOMLDecodeError:
        pass

    # A common user configuration stores prepend_keymap as an inline array.
    # Insert inline entries into that array. Compare the entire parsed document
    # afterward, so a lookalike in a comment/string can never modify other data.
    insertion = '\n# Added by Yazi Setup: previously unmapped shortcuts only\n' + ''.join(
        inline(entry) + ',\n' for entry in result.added)
    original_entries = parsed.get('mgr', {}).get('prepend_keymap', [])
    expected['mgr']['prepend_keymap'] = result.added + original_entries
    for match in re.finditer(r'(?m)^\s*(?:prepend_keymap|"prepend_keymap"|\'prepend_keymap\')\s*=\s*\[', existing):
        candidate = existing[:match.end()] + insertion + existing[match.end():]
        try:
            if tomllib.loads(candidate) == expected:
                result.content = candidate
                return result
        except tomllib.TOMLDecodeError:
            continue
    raise ValueError('Could not safely locate mgr.prepend_keymap for merging; use --skip-keymap and inspect keymap.toml.')


def confirm_merge(plan, dry_run=False, assume_merge=False):
    if not plan.added:
        return True
    print('Missing shortcuts: ' + ', '.join(' '.join(keys(entry)) for entry in plan.added))
    if dry_run:
        print('[dry-run] Existing keymap: ' + ('would add missing shortcuts (--merge-keymap).' if assume_merge else 'would ask whether to merge these missing shortcuts.'))
        return True
    if assume_merge:
        return True
    if not sys.stdin.isatty():
        print('Non-interactive install: existing keymap kept. Pass --merge-keymap to add missing shortcuts.')
        return False
    while True:
        try:
            answer = input('Merge these missing shortcuts into your existing keymap? [y/N]: ').strip().lower()
        except EOFError:
            print('No answer available; existing keymap left unchanged. Use --merge-keymap for unattended installs.')
            return False
        if answer in ('y', 'yes'):
            return True
        if answer in ('', 'n', 'no'):
            return False


def conflict_report(plan):
    lines = []
    for conflict in plan.conflicts:
        kept = '; '.join(' '.join(item['keys']) + ': ' + str(item['run']) for item in conflict['existing'])
        lines.append(' '.join(conflict['keys']) + ': kept ' + kept + '; setup proposed ' + str(conflict['requested']))
    return lines
