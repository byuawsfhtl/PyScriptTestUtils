#!/usr/bin/env node
import { PyScriptTestBridge } from "./PyScriptTestBridge";
declare function buildBridge(): PyScriptTestBridge;
declare const bridge: PyScriptTestBridge;
export { buildBridge, bridge };
