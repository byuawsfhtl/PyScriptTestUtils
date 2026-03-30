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
export declare class PyScriptTestBridge {
    private readonly handlers;
    addMethod(tsMethodName: string, handler: TestMethodHandler): void;
    processRequest(request: TestRequest): TestResponse;
}
