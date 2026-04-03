class CustomClassTS {
    constructor(public value: number, public myName: string) {}

    public equals(other: CustomClassTS): boolean {
        return this.value === other.value && this.myName === other.myName;
    }

    public toString(): string {
        return `${this.myName}: ${this.value}`;
    }

    public inspect(): string {
        return `CustomClassTS(value=${this.value}, myName=${this.myName})`;
    }

    public setValue(value: number): void {
        this.value = value;
    }

    public setMyName(myName: string): void {
        this.myName = myName;
    }

    public addToVal(increment: number): number {
        this.value += increment;
        return this.value;
    }

    public printNameAndValue(): void {
        console.log(`My name is ${this.myName} and my value is ${this.value}`);
    }
}