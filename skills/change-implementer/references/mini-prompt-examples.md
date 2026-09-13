# Mini-Prompt Examples

Each example shows a natural request and the mini-prompt generated from it after inspecting the codebase. Note how every section references concrete paths, symbols, and commands — never abstractions.

---

## Example 1 — Bug fix (backend)

**Request:** "Login trả 500 khi email có chữ in hoa"

```
### Task
Make email lookup case-insensitive in the login flow.

### Context
- Handler: src/auth/login.ts → `loginHandler()` calls `findUserByEmail(email)` (src/db/users.ts:42).
- `findUserByEmail` runs `WHERE email = $1` with the raw input; DB stores emails lowercased on signup (src/auth/signup.ts:31 uses `.toLowerCase()`).
- Existing tests: tests/auth/login.test.ts uses vitest, seeds via `createUser()` helper.

### Expected Result
`POST /login` with `Foo@Bar.com` authenticates the same user as `foo@bar.com`. No 500.

### Constraints
- Do not change the DB schema or add a migration.
- Do not alter signup behavior.
- Keep `findUserByEmail` signature unchanged (used in 3 other places).

### Implementation
1. Add failing test in tests/auth/login.test.ts: create user with lowercase email, login with mixed-case, expect 200.
2. In src/auth/login.ts, normalize with `email.trim().toLowerCase()` before calling `findUserByEmail` — mirrors signup.ts:31.
3. Run `npm test -- tests/auth/login.test.ts`.
```

---

## Example 2 — UI change (Flutter)

**Request:** "Đổi nút Save ở màn hình Settings thành màu primary và to hơn"

```
### Task
Restyle the Save button on SettingsScreen: primary color, larger size.

### Context
- Widget: lib/features/settings/presentation/settings_screen.dart:118 → `ElevatedButton(onPressed: _save, child: Text('Save'))`, no style override.
- Theme defines `AppButtonStyles.primaryLarge` in lib/core/theme/button_styles.dart:14, already used on lib/features/auth/presentation/login_screen.dart:92.
- Widget test exists: test/features/settings/settings_screen_test.dart finds button by `find.text('Save')`.

### Expected Result
Save button uses `AppButtonStyles.primaryLarge`, visually matches the Login button.

### Constraints
- Do not change `_save` logic or button label (test depends on text).
- Do not touch the theme file — reuse the existing style.

### Implementation
1. Set `style: AppButtonStyles.primaryLarge` on the ElevatedButton at settings_screen.dart:118.
2. Run `flutter analyze` and `flutter test test/features/settings/`.
```

---

## Example 3 — Add feature (CLI, Python)

**Request:** "Thêm flag --json cho lệnh list để in ra JSON"

```
### Task
Add a `--json` flag to the `list` subcommand that outputs results as JSON.

### Context
- CLI built with click: cli/commands/list.py → `@click.command("list")`, prints via `_render_table(items)`.
- `items` is `list[Item]`, `Item` is a dataclass (core/models.py:8) — serializable with `dataclasses.asdict`.
- Other commands (cli/commands/show.py:21) already have `--json` using `click.echo(json.dumps(..., indent=2))`.
- Tests: tests/cli/test_list.py uses `CliRunner`.

### Expected Result
`tool list --json` prints a JSON array of items; without the flag, behavior is unchanged.

### Constraints
- Table output must remain byte-identical to current output.
- Match the `--json` convention in show.py (same flag name, `indent=2`).

### Implementation
1. Add `@click.option("--json", "as_json", is_flag=True)` to list.py, copying the pattern from show.py:21.
2. Branch: if `as_json` → `click.echo(json.dumps([asdict(i) for i in items], indent=2))`, else existing `_render_table`.
3. Add test in tests/cli/test_list.py asserting `json.loads(result.output)` is a list.
4. Run `pytest tests/cli/test_list.py` and `ruff check cli/`.
```

---

## Example 4 — Remove behavior

**Request:** "Bỏ popup xác nhận khi xóa item, xóa luôn"

```
### Task
Remove the confirmation dialog before item deletion.

### Context
- src/components/ItemRow.tsx:44 → `onDelete` opens `<ConfirmDialog>` then calls `deleteItem(id)` on confirm.
- `ConfirmDialog` (src/components/ConfirmDialog.tsx) is also used by ProjectSettings.tsx — must not be deleted.
- Tests: src/components/__tests__/ItemRow.test.tsx has a test "asks for confirmation before delete".

### Expected Result
Clicking delete removes the item immediately; no dialog.

### Constraints
- Keep `ConfirmDialog` component intact (other usages).
- Keep `deleteItem` call and its error toast.

### Implementation
1. In ItemRow.tsx, call `deleteItem(id)` directly in the click handler; remove the dialog state and `<ConfirmDialog>` render.
2. Update the existing test: rename to "deletes immediately on click", assert `deleteItem` called once, no dialog queried.
3. Run `npm run typecheck && npm test -- ItemRow`.
```

---

## Anti-patterns

| Bad | Why | Fix |
|---|---|---|
| "Update the relevant handler" | No path — forces re-discovery during Implement | Name the file and function |
| "Follow project conventions" | Not actionable | Cite the specific file that shows the convention |
| "Verify it works" | No command | Name the exact test/lint/build command |
| Constraints section empty | Almost always wrong — something is always at risk | List callers, tests, and shared code that must not change |
| Mini-prompt longer than the change | Over-specified | Cut everything not needed to execute |
