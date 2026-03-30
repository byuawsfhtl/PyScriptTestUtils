export interface TestRequest {
    method: string;
    args: any[];
}

export interface TestResponse {
    success: boolean;
    result?: any;
    error?: string;
}

export type TestMethodHandler = (args: any[]) => TestResponse;

export class PyScriptTestBridge {
    private readonly handlers = new Map<string, TestMethodHandler>();

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
            return handler(request.args);
        } catch (error) {
            return {
                success: false,
                error: error instanceof Error ? error.message : String(error),
            };
        }
    }
}
