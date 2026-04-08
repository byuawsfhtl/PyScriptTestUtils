// import { jest } from "@jest/globals";

// NOTE for future developers: Ideally, this package should somehow support mocking.
// However, I can't currently figure out how to sucessfully identify and mock over helper functions/objects within the FUTs.
// I left the skeletal outline for the mock "structure" in commented-out code in case anyone would like to impliment it in the future.

// export interface MockSpec {
//     return_value?: any;
// }

export interface TestRequest {
    method: string;
    args: any[];
    // mocks?: Record<string, MockSpec>;
}

export interface TestResponse {
    success: boolean;
    result?: any;
    error?: string;
}

// export class MockContext {
//     private readonly specs: Record<string, MockSpec>;

//     constructor(rawMocks: Record<string, MockSpec> = {}) {
//         if (typeof rawMocks !== "object" || Array.isArray(rawMocks)) {
//             throw new TypeError("rawMocks must be a plain object");
//         }
//         this.specs = rawMocks;
//     }

//     get<T extends (...args: any[]) => any>(name: string, fallback: T): T {
//         if (typeof name !== "string" || !name) {
//             throw new TypeError("name must be a non-empty string");
//         }
//         if (typeof fallback !== "function") {
//             throw new TypeError("fallback must be a function");
//         }
//         const spec = this.specs[name];
//         if (spec === undefined) {
//             return fallback;
//         }
//         return ((..._args: any[]) => spec.return_value) as T;
//     }
// }

export type TestMethodHandler = (args: any[]) => any;

/**
 * A bridge that allows Python to call TypeScript functions. Constaints a map of method names to executables.
 * @param serializer - A function to serialize objects into consistent Json-like structures.
 * @param plainDeserializer - A function to deserialize objects into an expected custom class.
 */
export class PyScriptTestBridge {

    constructor(
        private readonly serializer: (data: any) => any = (data: any) => data,
        private readonly plainDeserializer: (data: any) => any = (data: any) => data,
    ) {}

    private readonly handlers = new Map<string, TestMethodHandler>();
    private readonly deserializer: any = (data: any) => {
        if (Array.isArray(data)) {
            try { return data.map(this.plainDeserializer); } catch { return data; }
        }
        try { return this.plainDeserializer(data); } catch { return data; }
    };
    private readonly mockReturns = new Map<string, any[]>();
    private readonly mockSideEffects = new Map<string, (...args: any[]) => any>();

    addMethod(tsMethodName: string, handler: TestMethodHandler): void {
        if (!tsMethodName || !String(tsMethodName).trim()) {
            throw new Error("tsMethodName must be non-empty");
        }
        if (this.handlers.has(tsMethodName)) {
            throw new Error(`Duplicate TypeScript method: ${tsMethodName}`);
        }
        this.handlers.set(tsMethodName, handler);
    }

    // addMock(tsMethodName: string, returnValue: any): void {
    //     if (!tsMethodName || !String(tsMethodName).trim()) {
    //         throw new Error("tsMethodName must be non-empty");
    //     }
    //     if (!this.handlers.has(tsMethodName)) {
    //         throw new Error(`Unknown method: ${tsMethodName}`);
    //     }
    //     if (!this.mockReturns.has(tsMethodName)) {
    //         this.mockReturns.set(tsMethodName, [returnValue]);
    //     } else {
    //         this.mockReturns.get(tsMethodName)!.push(returnValue);
    //     }
    // }

    // addMockSideEffect(tsMethodName: string, sideEffect: (...args: any[]) => any): void {
    //     if (!tsMethodName || !String(tsMethodName).trim()) {
    //         throw new Error("tsMethodName must be non-empty");
    //     }
    //     if (!this.handlers.has(tsMethodName)) {
    //         throw new Error(`Unknown method: ${tsMethodName}`);
    //     }
    //     this.mockSideEffects.set(tsMethodName, sideEffect);
    // }

    processRequest(request: TestRequest): TestResponse {
        const handler = this.handlers.get(request.method);
        if (!handler) {
            return { success: false, error: `Unknown method: ${request.method}` };
        }
        try {
            // const mockCtx = new MockContext(request.mocks ?? {});
            const result = handler(this.deserializer(request.args));
            try { 
                return {success: true, result: this.serializer(result)};
            } catch {
                return {success: true, result: result};
            }
        } catch (error) {
            return {
                success: false,
                error: error instanceof Error ? error.message : String(error),
            };
        }
    }

    /**
     * Read one JSON-RPC request from argv, write one JSON line to stdout.
     * Call this only from your entry script inside `if (require.main === module) { ... }`
     * so `require.main` refers to that script (not this module).
     */
    runCli(argv: string[] = process.argv.slice(2)): void {
        if (!Array.isArray(argv)) {
            throw new TypeError("argv must be an array of strings");
        }

        try {
            const request = JSON.parse(argv[0]) as TestRequest;
            if (!request || typeof request !== "object" || Array.isArray(request)) {
                throw new TypeError("Parsed request must be a plain object");
            }
            if (typeof request.method !== "string" || !Array.isArray(request.args)) {
                throw new TypeError("Request must include string method and array args");
            }
            const response = this.processRequest(request);
            console.log(JSON.stringify(response));
        } catch (error) {
            const errorResponse: TestResponse = {
                success: false,
                error: error instanceof Error ? error.message : String(error),
            };
            console.log(JSON.stringify(errorResponse));
        }
    }
}
