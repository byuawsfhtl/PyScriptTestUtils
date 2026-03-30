/**
 * Consumer entry: register domain handlers, then serve JSON-RPC lines from argv.
 * FlexibleDate comes from the local package (file:../FlexibleDate/FlexibleDateTS) so
 * imports work from dist/ (relative ../ paths would break once compiled into dist/).
 */
import FlexibleDate from "flexibledatets";
import { PyScriptTestBridge } from "./PyScriptTestBridge";

function serializeFlexibleDate(fd: FlexibleDate): any {
    return {
        likelyYear: fd.likelyYear,
        likelyMonth: fd.likelyMonth,
        likelyDay: fd.likelyDay,
    };
}

function deserializeFlexibleDate(data: any): FlexibleDate {
    return new FlexibleDate(data.likelyDay, data.likelyMonth, data.likelyYear);
}

const bridge = new PyScriptTestBridge();

bridge.addMethod("createFlexibleDate", (args) => {
    const [dateString] = args;
    const fd = new FlexibleDate(dateString);
    return { success: true, result: serializeFlexibleDate(fd) };
});

bridge.addMethod("createFlexibleDateFromFormalDate", (args) => {
    const [formalDateString] = args;
    const fdFromFormal = new FlexibleDate(null, null, null);
    const result = fdFromFormal.createFlexibleDateFromFormalDate(formalDateString);
    return { success: true, result: serializeFlexibleDate(result) };
});

bridge.addMethod("compareDates", (args) => {
    const [date1Data, date2Data] = args;
    const fd1 = deserializeFlexibleDate(date1Data);
    const fd2 = deserializeFlexibleDate(date2Data);
    const score = fd1.compareDates(fd2);
    return { success: true, result: score };
});

bridge.addMethod("combineFlexibleDates", (args) => {
    const [datesData] = args;
    const dates = datesData.map((d: any) => deserializeFlexibleDate(d));
    const fdTemp = new FlexibleDate(null, null, null);
    const combined = fdTemp.combineFlexibleDates(dates);
    return { success: true, result: serializeFlexibleDate(combined) };
});

bridge.addMethod("toString", (args) => {
    const [fdData] = args;
    const fdForString = deserializeFlexibleDate(fdData);
    return { success: true, result: fdForString.toString() };
});

bridge.addMethod("valueOf", (args) => {
    const [fdDataValue] = args;
    const fdForValue = deserializeFlexibleDate(fdDataValue);
    return { success: true, result: fdForValue.valueOf() };
});

bridge.addMethod("testBool", (args) => {
    const [fdDataBool] = args;
    const fdForBool = deserializeFlexibleDate(fdDataBool);
    return { success: true, result: fdForBool.valueOf() };
});

bridge.addMethod("testStr", (args) => {
    const [fdDataStr] = args;
    const fdForStr = deserializeFlexibleDate(fdDataStr);
    return { success: true, result: fdForStr.toString() };
});

bridge.addMethod("testRepr", (args) => {
    const [fdDataRepr] = args;
    const fdForRepr = deserializeFlexibleDate(fdDataRepr);
    return { success: true, result: fdForRepr.inspect() };
});

bridge.addMethod("test_equals", (args) => {
    const [fdDataEquals1, fdDataEquals2] = args;
    const fdForEquals1 = deserializeFlexibleDate(fdDataEquals1);
    const fdForEquals2 = deserializeFlexibleDate(fdDataEquals2);
    return { success: true, result: fdForEquals1.equals(fdForEquals2) };
});

bridge.addMethod("testValidator", (args) => {
    try {
        const [fdDataValidator] = args;
        const fdForValidator = deserializeFlexibleDate(fdDataValidator);
        return { success: true, result: serializeFlexibleDate(fdForValidator) };
    } catch {
        return { success: true, result: "ValueError" };
    }
});

if (require.main === module) {
    bridge.runCli(process.argv.slice(2));
}
