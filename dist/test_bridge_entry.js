#!/usr/bin/env node
"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.bridge = void 0;
exports.buildBridge = buildBridge;
/**
 * Consumer entry: register domain handlers, then serve JSON-RPC lines from argv.
 * Adjust the FlexibleDate import to your package layout when publishing elsewhere.
 */
const FlexibleDateTS_1 = __importDefault(require("../FlexibleDate/FlexibleDateTS/dist/FlexibleDateTS"));
const PyScriptTestBridge_1 = require("./PyScriptTestBridge");
function serializeFlexibleDate(fd) {
    return {
        likelyYear: fd.likelyYear,
        likelyMonth: fd.likelyMonth,
        likelyDay: fd.likelyDay,
    };
}
function deserializeFlexibleDate(data) {
    return new FlexibleDateTS_1.default(data.likelyDay, data.likelyMonth, data.likelyYear);
}
function buildBridge() {
    const bridge = new PyScriptTestBridge_1.PyScriptTestBridge();
    bridge.addMethod("createFlexibleDate", (args) => {
        const [dateString] = args;
        const fd = new FlexibleDateTS_1.default(dateString);
        return { success: true, result: serializeFlexibleDate(fd) };
    });
    bridge.addMethod("createFlexibleDateFromFormalDate", (args) => {
        const [formalDateString] = args;
        const fdFromFormal = new FlexibleDateTS_1.default(null, null, null);
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
        const dates = datesData.map((d) => deserializeFlexibleDate(d));
        const fdTemp = new FlexibleDateTS_1.default(null, null, null);
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
        }
        catch {
            return { success: true, result: "ValueError" };
        }
    });
    return bridge;
}
const bridge = buildBridge();
exports.bridge = bridge;
if (require.main === module) {
    const argv = process.argv.slice(2);
    if (argv.length === 0) {
        console.error("Usage: node test_bridge_entry.js <json_request>");
        process.exit(1);
    }
    try {
        const request = JSON.parse(argv[0]);
        const response = bridge.processRequest(request);
        console.log(JSON.stringify(response));
    }
    catch (error) {
        const errorResponse = {
            success: false,
            error: error instanceof Error ? error.message : String(error),
        };
        console.log(JSON.stringify(errorResponse));
    }
}
