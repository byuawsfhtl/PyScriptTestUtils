import { PyScriptTestBridge } from "../../src/PyScriptTestBridge";

import { addTwoInts, multiplyByTen } from "./ts/randomFuncs";

const bridge = new PyScriptTestBridge();

bridge.addMethod("multiplyByTen", (args) => {
    return multiplyByTen(args[0]);
});

bridge.addMethod("addTwoInts", (args) => {
    return addTwoInts(args[0], args[1]);
});

if (require.main === module) {
    bridge.runCli();
}