# Did a package resource disappear between wheels?

**Audience:** Python package maintainers reviewing release artifacts. This is a
reproducible **synthetic exercise**, not a real incident or a security benchmark.
AI-assisted tutorial and fixtures; no independent user validation yet.

A version bump changes metadata even when the package payload is identical. This
trial includes that control so a nonzero finding count is not mistaken for a bug.
The second candidate intentionally omits one template. You decide whether the
removal is intended; Wheel Delta reports bytes and paths, not compatibility.

## Run locally (Python 3.10+)

Download this repository's source and open its root in a terminal. Create a venv
and install the Wheel Delta wheel downloaded from **this repository's v0.1.0
GitHub Release** (not an unrelated same-name PyPI package):

```sh
python -m venv .venv
```

Activate with `.venv\Scripts\Activate.ps1` in PowerShell, or
`source .venv/bin/activate` in a POSIX shell. If activation is blocked, use the
venv Python's explicit path rather than changing your execution policy.

```sh
python -m pip install --no-index --no-deps /path/to/wheel_delta-0.1.0-py3-none-any.whl
python scripts/make_resource_trial.py trial-inputs
python -m wheel_delta trial-inputs/before/example_resource_pkg-1.0-py3-none-any.whl trial-inputs/version-only/example_resource_pkg-1.1-py3-none-any.whl --json version-only.json --html version-only.html
python -m wheel_delta trial-inputs/before/example_resource_pkg-1.0-py3-none-any.whl trial-inputs/missing-resource/example_resource_pkg-1.1-py3-none-any.whl --json missing-resource.json --html missing-resource.html
```

Use **new** output names/directories on each run. Neither the generator nor the
report writer overwrites existing outputs. An I/O failure may leave partial
outputs. The generator needs no dependencies and writes only the three fixtures;
it does not install them, import their code, or connect to a network.

## Check the result before interpreting it

| Comparison | Metadata changes | Payload changes | Meaning in this exercise |
| --- | --- | --- | --- |
| Before vs version-only | METADATA and RECORD | None | Intended version bump, not a missing resource |
| Before vs missing-resource | METADATA and RECORD | `example_resource_pkg/templates/welcome.txt` removed | Deliberately missing synthetic template |

Open the HTML files locally, or inspect `changes` in the JSON. The paths under
`{dist-info}/` are normalized across versions, not hidden. No file contents appear
in reports. JSON from these file inputs has `synthetic_demo: false`: that field
means the built-in `--demo` mode was not used, **not** that these fixtures are real.

This command isolates removed payload paths for manual review:

```sh
python -c "import json; r=json.load(open('missing-resource.json', encoding='utf-8')); print([c['path'] for c in r['changes'] if c['kind']=='payload' and c['change']=='removed'])"
```

Expected: `['example_resource_pkg/templates/welcome.txt']`. Change the JSON filename
to `version-only.json` and the expected list is `[]`.

**Do not use `--fail-on-findings` as a missing-resource-only gate.** Both comparisons
have findings and return exit 1 with that option, because metadata counts too.
Without it, exit 0 only means analysis completed. The filter above is a reading
aid, not a complete release policy: intentional removals need review and other
regressions may not be removed files.

## Boundaries and a useful feedback question

Wheel Delta compares two artifacts; it does not establish that either was built
correctly. It does not validate RECORD, execute packages, test resource loading,
or establish API/ABI compatibility or malware safety. The fixture tests verify
their own RECORD hashes separately, not a new scanner capability. For actual
releases, also test installed behavior and use your existing packaging checks.
Filenames in reports can be sensitive; do not upload private wheels or reports.

If you try this exercise: **could you distinguish the metadata-only change from
the missing template, and what was confusing or redundant with your existing
tools?** Optional GitHub feedback should contain only synthetic information. No
star, account creation, or feedback submission is needed to run the local trial.

## 中文速读

这是供 Python 包维护者试用的合成练习，不是真实事故。第一组只改版本，
METADATA 和 RECORD 会变化，但 payload 不变；第二组故意漏掉一个模板。
按上面的命令生成三个 wheel 并比较，打开 HTML 或读取 JSON 即可区分两组。
不要安装这些输入样例；只安装本仓库 Release 提供的 Wheel Delta 工具。

`--fail-on-findings` 对两组都会返回 1，不能把它当成“仅丢失资源才失败”的门禁。
JSON 的 `synthetic_demo: false` 只表示没有用内置 `--demo`，本练习仍全部为合成数据。
工具不判定删除是否合理、不验证 RECORD、不验证安装后行为或兼容性。
若愿意反馈，请说清哪里难懂、现有工具是否已经足够，只提供合成资料。
