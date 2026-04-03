import CustomClassTS from "./CustomClassTS"

function multiplyByTen(a: number): number {
    return a * 10
}

function addTwoInts(a: number, b: number): number {
    return a + b
}

function createCustomClass(value: number, my_name: string): CustomClassTS {
    return new CustomClassTS(value, my_name)
}

function addThreeInts(a: number, b: number, c: number): number {
    const step1 = addTwoInts(a, b)
    const step2 = addTwoInts(step1, c)
    return step2
}

export { multiplyByTen, addTwoInts, createCustomClass, addThreeInts }