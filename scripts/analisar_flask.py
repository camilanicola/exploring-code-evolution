"""Gera o relatório GitEvo e registra as evidências usadas no README."""

import argparse
import json
import platform
from collections import Counter, defaultdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from git import Repo
from gitevo import GitEvo
from gitevo.reports import python
from treeminer.repo import TreeMinerRepo


ROOT = Path(__file__).resolve().parents[1]
REVISION = "49943b5a94413a530761350f04e896f76e8d620e"
TYPING_MERGE = "1a8549debb914eecc85cf63034093b55792c7e8f"


def count_returns(repo_path, revision):
    """Aplica a mesma regra de retorno do GitEvo, separando diretórios."""
    counts = defaultdict(Counter)
    for commit in TreeMinerRepo(str(repo_path), single=revision).commits:
        for file in commit.all_files([".py"]):
            group = (
                "src/flask" if file.path.startswith("src/flask/")
                else "tests" if file.path.startswith("tests/")
                else "outros"
            )
            for node in file.tree_nodes:
                if node.type == "function_definition":
                    key = "yes" if node.child_by_field_name("return_type") else "no"
                    counts[group][key] += 1
    return {
        group: {key: count[key] for key in ("yes", "no")}
        for group, count in sorted(counts.items())
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repositorio", type=Path, help="Clone local completo do Flask")
    args = parser.parse_args()
    repo_path = args.repositorio.resolve()
    repo = Repo(repo_path)
    if repo.head.commit.hexsha != REVISION:
        parser.error(f"O clone deve estar na revisão {REVISION} para reproduzir a análise.")

    output = ROOT / "relatorios"
    output.mkdir(exist_ok=True)
    evo = GitEvo(
        repo=str(repo_path), extension=".py", from_year=2010, to_year=2026,
        date_unit="year", report_filename=str(output / "flask"), report_title="Flask",
    )
    python.metrics(evo)
    results = evo.run()
    if len(results) != 1 or len(results[0].project_result.commit_results) != 17:
        raise RuntimeError("O GitEvo não produziu as 17 amostras anuais esperadas.")

    commits = results[0].project_result.commit_results
    samples = [
        {"ano": commit.date.year, "data": commit.date.isoformat(), "commit": commit.hash}
        for commit in commits
    ]
    merge = repo.commit(TYPING_MERGE)
    evidence = {
        "repositorio": "https://github.com/pallets/flask",
        "head": REVISION,
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "gitevo": version("gitevo"),
        "tree_sitter": version("tree-sitter"),
        "tree_sitter_python": version("tree-sitter-python"),
        "amostragem": "Primeiro commit encontrado pelo GitEvo em cada ano, por data do committer.",
        "amostras": samples,
        "tipagem_antes_do_merge": {
            "commit": merge.parents[0].hexsha,
            "contagens": count_returns(repo_path, merge.parents[0].hexsha),
        },
        "tipagem_depois_do_merge": {
            "commit": merge.hexsha,
            "data": merge.committed_datetime.isoformat(),
            "contagens": count_returns(repo_path, merge.hexsha),
        },
        "retornos_por_diretorio_2026": {
            "commit": commits[-1].hash,
            "contagens": count_returns(repo_path, commits[-1].hash),
        },
    }
    (output / "evidencias.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
