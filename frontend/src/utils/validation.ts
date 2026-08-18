export function validateSkinName(name: string): string | null {
    if (name.length == 0) {
        return "Skin Name is empty.";
    }

    return null;
}

export function validateFloatValue(value: string): string | null {
    if (!value) {
        return "Float Value is empty.";
    }
    let number = Number(value);
    if (Number.isNaN(number)) {
        return "Entered value is not a float.";
    }
    if (number >= 1.0 || number <= 0.0) {
        return "Entered float value is not between 0 and 1.";
    }

    return null;
}

export function validatePurchasePrice(value: string): string | null {
    if (!value) {
        return "Purchase Price is empty.";
    }
    let number = Number(value);
    if (Number.isNaN(number)) {
        return "Entered value is not a number.";
    }
    if (number <= 0.0) {
        return "Entered purchase price is not positive.";
    }

    return null;
}

export function validateTransactionType(value: string): string | null{
    if (!value) {
        return "Transaction type is empty.";
    }
    return null;
}

export function validateTransactionValue(value: string): string | null {
    if (!value) {
        return "transaction value is empty.";
    }
    let number = Number(value);
    if (Number.isNaN(number)) {
        return "Entered value is not a number.";
    }

    return null;
}

export function validateTransactionDetails(value: string): string | null{
    if (!value) {
        return "Transaction details is empty.";
    }
    return null;
}