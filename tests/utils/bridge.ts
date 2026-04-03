import { PyScriptTestBridge } from "../../src/PyScriptTestBridge";

import { addTwoInts, createCustomClass, multiplyByTen } from "./ts/randomFuncs";
import CustomClassTS from "./ts/CustomClassTS";

function serializeCustomClass(customClass: CustomClassTS): any {
    if (customClass.constructor.name !== "CustomClassTS") {
        return customClass;
    }
    return {
        value: customClass.value,
        myName: customClass.myName
    };
}
function deserializeCustomClass(data: any): CustomClassTS {
    if (!("value" in data && "myName" in data)) {
        return data;
    }
    return new CustomClassTS(data.value, data.myName);
}

const bridge = new PyScriptTestBridge(serializeCustomClass, deserializeCustomClass);

bridge.addMethod("multiplyByTen", (args) => {
    return multiplyByTen(args[0]);
});

bridge.addMethod("addTwoInts", (args) => {
    return addTwoInts(args[0], args[1]);
});

bridge.addMethod("createCustomClass", (args) => {
    return createCustomClass(args[0], args[1]);
});

bridge.addMethod("CustomClassTS.getNameAndValue", (args) => {
    return args[0].getNameAndValue();
});

if (require.main === module) {
    bridge.runCli();
}