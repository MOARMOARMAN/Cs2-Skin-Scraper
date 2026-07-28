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
        return "Entered value is not a float.";
    }
    if (number <= 0.0) {
        return "Entered purchase price is not positive.";
    }

    return null;
}