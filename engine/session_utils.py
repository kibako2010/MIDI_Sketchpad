import os
from typing import Dict, List


def part_name_from_path(path: str) -> str:
    base = os.path.basename(path)
    name, _ = os.path.splitext(base)
    return name


def resolve_part_file_map(part_files: List[str], session_path: str) -> Dict[str, str]:
    """
    session.json の part_files から実在パスを解決。
    保存時の相対パス・移動後のsessionにも耐える。
    """
    result: Dict[str, str] = {}
    session_dir = os.path.dirname(os.path.abspath(session_path))

    for fp in part_files or []:
        candidates = []
        if os.path.isabs(fp):
            candidates.append(fp)
        else:
            candidates.append(os.path.abspath(fp))
            candidates.append(os.path.join(session_dir, fp))
            candidates.append(os.path.join(session_dir, os.path.basename(fp)))

        found = None
        for c in candidates:
            if os.path.exists(c):
                found = c
                break

        if found:
            result[part_name_from_path(found)] = found

    return result
