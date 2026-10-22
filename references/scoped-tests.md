# Running tests — scoped to the diff

Shared by `/pr` (Step 4), `/assign` (the worker's *Verify* bullet) and `/bugfix`. A developer's machine cannot take every submodule's whole
suite plus a build at once, and a diff of a few files does not need it.

1. **Scope.** Changed files = `git -C <path> diff --name-only <default>...HEAD` plus uncommitted, minus generated files (what `make gen`
   or the stack's generator writes) and docs. Run:
   - **Go:** the packages that hold a changed `.go` file (`go test ./<dir>/`), plus their direct dependents (packages whose
     `go list -f '{{ .ImportPath }}: {{ join .Imports " " }}' ./...` line, other than the package's own, names a changed package) when that is 10 packages or fewer;
     more → the changed packages only, and the report says so.
   - **Node / Next.js:** `<package manager> exec vitest related --run <changed source files>` (jest: `jest --findRelatedTests <files>`);
     a changed test file is passed as it is. Not the project's `test` script when that script runs everything.
   - **Python:** `pytest` on the changed test files and the tests that import a changed module.
   No related test found → the report says `no related tests`; that is not a failure.
2. **The whole suite runs only when** the diff touches a shared or configuration file — `go.mod`, `go.sum`, `package.json`, a lockfile,
   `tsconfig*`, the vitest / jest config, `pyproject.toml` / `requirements*`, a `Makefile` — or the user passed `--full`. Then the stack's
   usual command (Makefile `test` target → package-manager `test` script → `go test ./...` / `pytest`).
3. **Build** (`build:stg` and the like) runs only when the project's own `CLAUDE.md` requires it before a commit or a PR, and then on its
   own, after the tests have passed. A test run never starts one.
4. **Tests first, then the build.** Within a submodule the build never starts before its tests have passed. Submodules may be tested in
   parallel.
5. **A failure outside the diff's scope** (the failing test is in no changed package or file and imports none) is run again, that test
   only, on the base before anything stops: in a throwaway worktree of `origin/<tracking branch>`
   (`git -C <path> worktree add --detach <scratchpad dir> origin/<tracking branch>`, removed afterwards; a Node project reuses the
   checkout's installed dependencies). Go: `go test <pkg> -run '<name>'`; vitest: `vitest run <file> -t '<name>'`; pytest: the node id.
   - Fails there too → report `pre-existing on origin/<tracking branch>: <test>`; it does **not** block the PR.
   - Passes there → the branch broke it: blocking, as any failure in the diff's scope.
   - Cannot be run on the base → stop and tell the dev; never guess it was already red.
6. **Say what ran.** The report has one line per submodule: `tests: scoped (<n> packages | files)` or `tests: full — <the file that
   touched, or --full>`, plus any `pre-existing on …` line.
