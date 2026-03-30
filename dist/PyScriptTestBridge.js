"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PyScriptTestBridge = void 0;
class PyScriptTestBridge {
    constructor() {
        this.handlers = new Map();
    }
    addMethod(tsMethodName, handler) {
        if (!tsMethodName || !String(tsMethodName).trim()) {
            throw new Error("tsMethodName must be non-empty");
        }
        if (this.handlers.has(tsMethodName)) {
            throw new Error(`Duplicate TypeScript method: ${tsMethodName}`);
        }
        this.handlers.set(tsMethodName, handler);
    }
    processRequest(request) {
        const handler = this.handlers.get(request.method);
        if (!handler) {
            return { success: false, error: `Unknown method: ${request.method}` };
        }
        try {
            return handler(request.args);
        }
        catch (error) {
            return {
                success: false,
                error: error instanceof Error ? error.message : String(error),
            };
        }
    }
}
exports.PyScriptTestBridge = PyScriptTestBridge;
