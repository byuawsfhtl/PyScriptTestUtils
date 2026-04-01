export interface TestRequest {
    method: string;
    args: any[];
}

export interface TestResponse {
    success: boolean;
    result?: any;
    error?: string;
}

export type TestMethodHandler = (args: any[]) => any;

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

    addMethod(tsMethodName: string, handler: TestMethodHandler): void {
        if (!tsMethodName || !String(tsMethodName).trim()) {
            throw new Error("tsMethodName must be non-empty");
        }
        if (this.handlers.has(tsMethodName)) {
            throw new Error(`Duplicate TypeScript method: ${tsMethodName}`);
        }
        this.handlers.set(tsMethodName, handler);
    }

    processRequest(request: TestRequest): TestResponse {
        const handler = this.handlers.get(request.method);
        if (!handler) {
            return { success: false, error: `Unknown method: ${request.method}` };
        }
        try {
            console.error(request);
            console.error(this.deserializer(request.args));
            const result = handler(this.deserializer(request.args))
            console.error(result);
            console.error(this.serializer(result));
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
