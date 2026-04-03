function addTwoInts(a: number, b: number): number {
    return a + b
}

function createCustomClass(value: number, my_name: string): CustomClassTS {
    return new CustomClassTS(value, my_name)
}

function printCustomClass(customClass: CustomClassTS): void {
    customClass.printNameAndValue()
}
    
function addThreeInts(a: number, b: number, c: number): number {
    const step1 = addTwoInts(a, b)
    const step2 = addTwoInts(step1, c)
    return step2
}