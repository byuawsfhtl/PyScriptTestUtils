# PyScriptTestUtils

A package that runs pytest-style checks concurrently in Python and TypeScript so dual-language libraries can enforce the same behavior in both implementations.

## Architecture

- `**PyScriptTestRunner**` (Python): register one **named** Python function per operation with the TypeScript RPC name your Node bridge expects, then call `run` with the same `test_data` shape as before.
- `**PyScriptTestBridge`** (TypeScript): register handlers with `addMethod(tsName, (args) => response)`. The compiled `**test_bridge_entry.js`** is invoked by the runner via `node`; it parses one JSON request from argv and prints one JSON response.

## Python: registration and `run`

```python
runner = PyScriptTestRunner(
    "Path/to/built/test/bridge.js",
    (Optional) serializer = function to serialize objects into consistent Json-like structures,
    (Optional) deserializer = function to deserialize objects into an expected custom class.
)

def create_flexible_date(arg1, arg2, ...) -> FlexibleDate:
    some code...
    return flexible_date_object

runner.add_method(create_flexible_date, "createFlexibleDate", (Optional) executor=lambda args: create_flexible_date(args[0], args[1], ...))
runner.add_method(combine_flexible_dates, "combineFlexibleDates", (Optional) ts_pack_input=True)
# ...

py_result, ts_result = runner.run(
    "create_flexible_date",
    "createFlexibleDate",
    test_data,
)
```

Rules:

- `**add_method(py_callable, ts_method_name, *, ts_pack_input=False)**`  
  - `path/to/brige` must be the path to the **built** dist of the ts bridge, usually within a dist/ dir. Ex: `Path(__file__).resolve().parent() / "dist" / bridge.js`
  - `py_callable` must be a **named** function (not a lambda). The registry key is `py_callable.__name__` (what you pass as the first argument to `run`).  
  - `ts_method_name` must match `addMethod` on the TS side and the JSON `method` field.  
  - `executor` is some exeutable that processes the test data if neccesary.
  - `ts_pack_input=True`: for this operation the runner sends `args: [input_data]` to Node (single array argument). Use this for TS handlers that expect one aggregate argument (for example `combineFlexibleDates` with `const [datesData] = args`).
- `**run(python_name, ts_name, test_data)`** checks that `ts_name` matches the name registered for `python_name`.
- By default, registered Python callables receive a **single** argument: `test_data["input"]`, and returns the (optionally) serialized result of running the callable on the argument. If more arguments are needed, or if other post-processing on the output is needed, provide a test executor.
- Serializers and deserializers are optional. If a function is meant to return or take in a custom class, the runner must be provided with (de)serialization function(s), otherwise the data will be treated as raw types (bool, int, float, str, etc...). By default, the deserializer is capable of deserializing lists, so the provided deserialization function only needs to support deserialiation into the given class. The serializer does not support this.

## TypeScript: `test_bridge.ts`

The test bridge contains all that information neccessary for the python runner to call the TS functions under test. It is instantiated with optional serializer and deserializer parameters like the runner.

**Example:**

```ts
function serializeFlexibleDate(fd: FlexibleDate): any {
    if (fd.constructor.name === "FlexibleDate") {
        some code...
        return jsonLikeObject;
    }
    return fd
}

function deserializeFlexibleDate(data: any): FlexibleDate {
    if (can serialize to FlexibleDate...) {
        return new FlexibleDate(serialization logic...);
    }
    return data;
}

const bridge = new PyScriptTestBridge(serializeFlexibleDate, deserializeFlexibleDate);

bridge.addMethod("createFlexibleDate", (args) => new FlexibleDate(args[0]));
```

Rules:

`**addMethod("TSFunctionName, exector)**`
    - `TSFunctionName` must exactly match an `add_method()` entry on the cooresponding test runner. This is how the runner knows which function to run within the bridge.
    - `executor` must be the test executor function which runs the function under test. Unlike the runner, the bridge has no default executor, and so an executor must be provided with each `addMethod()` call.

**Serializer and Deserializer**
    - Unlike the runner, the bridge has no automatic serialization handling. This is a result of differences between Python and TypeScript runtime behavior. Thus, the (de)serialization functions must recognize whether the objects being passed into them can be (de)serialized as intended.
    - Alternatively, it is possible to have multiple bridge instances/files with and without (de)serializers as needed, though this is not recommended unless neccessary.

## RPC argument list (`args`)

The subprocess request is `{ "method": string, "args": any[], "mocks": object }`.

- For most operations the runner sets `**args`** from `test_data["input"]` as:
  - `[input_data]` when `input_data` is not a `list`,
  - or `**input_data` as-is** when it is already a `list`.
- When `**ts_pack_input=True`**, the runner always sends `**args: [input_data]`** (one element), so the TS handler uses `const [x] = args` (for example a list of serialized dates).

Align Python `input_data` in tests with this contract so both sides see the same logical inputs.

## Test Examples

```python
class TestIdenticalDates:
    """Test comparison of identical dates returns perfect score of 100."""

    test_cases = [
            {
                "input": [
                    {"likelyYear": 2020, "likelyMonth": 1, "likelyDay": 15},
                    {"likelyYear": 2020, "likelyMonth": 1, "likelyDay": 15}
                ],
                "expected": 100,
                "description": "identical full dates"
            },
            {
                "input": [
                    {"likelyYear": 2020, "likelyMonth": 5, "likelyDay": None},
                    {"likelyYear": 2020, "likelyMonth": 5, "likelyDay": None}
                ],
                "expected": 100,
                "description": "identical year-month dates"
            },
            {
                "input": [
                    {"likelyYear": 1995, "likelyMonth": None, "likelyDay": None},
                    {"likelyYear": 1995, "likelyMonth": None, "likelyDay": None}
                ],
                "expected": 100,
                "description": "identical year-only dates"
            }
        ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda x: x['description'])
    def test_identical_full_dates(self, test_case):
        test_data = {"input": test_case["input"], "expected": test_case["expected"], "mocks": {}}
        py_result, ts_result = runner.run(
            "compare_two_dates",
            "compareDates",
            test_data
        )
        assert py_result == test_case["expected"], f"Python failed for {test_case['description']}"
        assert ts_result == test_case["expected"], f"TypeScript failed for {test_case['description']}"
        runner.assert_strict_parity(py_result, ts_result, test_case['description'])
```

## Notes

- When testing construction of custom classes, the runner will attempt to deserialize the TS result via the provided deserializer function. This means that expected test results **can** be custom classes.
- When testing custom class methods, the runner cannot deserialize those custom classes, meaning that the input test-data must be provided pre-serialized.


## Developing

```bash
npm ci
npm run build
```

Requires Node.js and npm.