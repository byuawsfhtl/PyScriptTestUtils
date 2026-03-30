# PyScriptTestUtils

A package that runs pytest-style checks concurrently in Python and TypeScript so dual-language libraries can enforce the same behavior in both implementations.

## Architecture

- **`PyScriptTestRunner`** (Python): register one **named** Python function per operation with the TypeScript RPC name your Node bridge expects, then call `run` / `run_dual_test` with the same `test_data` shape as before.
- **`PyScriptTestBridge`** (TypeScript): register handlers with `addMethod(tsName, (args) => response)`. The compiled **`test_bridge_entry.js`** is invoked by the runner via `node`; it parses one JSON request from argv and prints one JSON response.

## Python: registration and `run`

```python
runner = PyScriptTestRunner()

def create_flexible_date(input_data):
    result = my_create_flexible_date(input_data)
    return serialize_if_needed(result)

runner.add_method(create_flexible_date, "createFlexibleDate")
runner.add_method(combine_flexible_dates, "combineFlexibleDates", ts_pack_input=True)
# ...

py_result, ts_result = runner.run(
    "create_flexible_date",
    "createFlexibleDate",
    test_data,
)
```

Rules:

- **`add_method(py_callable, ts_method_name, *, ts_pack_input=False)`**  
  - `py_callable` must be a **named** function (not a lambda). The registry key is `py_callable.__name__` (what you pass as the first argument to `run`).  
  - `ts_method_name` must match `addMethod` on the TS side and the JSON `method` field.  
  - **`ts_pack_input=True`**: for this operation the runner sends `args: [input_data]` to Node (single array argument). Use this for TS handlers that expect one aggregate argument (for example `combineFlexibleDates` with `const [datesData] = args`).
- **`run(python_name, ts_name, test_data)`** checks that `ts_name` matches the name registered for `python_name`.
- Registered Python callables receive a **single** argument: `test_data["input"]`. Shape the input in your tests so each callable can implement the operation (unwrap lists, deserialize dicts to domain objects, etc.).
- Return **JSON-serializable** values from Python (or the same shapes your TS bridge returns). The runner no longer auto-serializes domain types; keep that logic in your registered functions.

## TypeScript: `test_bridge_entry.ts`

This repo ships an example entry file that registers FlexibleDate operations and imports the sibling **`../FlexibleDate/FlexibleDateTS/dist/FlexibleDateTS`** build. For your own repo, point that import at your published or local TS package and keep the same `addMethod` names as on the Python side.

Build output goes to **`dist/test_bridge_entry.js`**. The Python runner defaults to **`package_root / "dist" / "test_bridge_entry.js"`**.

## RPC argument list (`args`)

The subprocess request is `{ "method": string, "args": any[], "mocks": object }`.

- For most operations the runner sets **`args`** from `test_data["input"]` as:
  - `[input_data]` when `input_data` is not a `list`,
  - or **`input_data` as-is** when it is already a `list` (so it becomes multiple `args` elements, matching the old behavior for `compareDates`, `test_equals`, etc.).
- When **`ts_pack_input=True`**, the runner always sends **`args: [input_data]`** (one element), so the TS handler uses `const [x] = args` (for example a list of serialized dates).

Align Python `input_data` in tests with this contract so both sides see the same logical inputs.

## Developing

```bash
npm ci
npm run build
```

Requires Node.js and npm. The example bridge import expects the FlexibleDate TS package to be built (`npm run build` in that repo) when using the default relative path.
