import { useState } from 'react';
import {
    addSkin, type NewSkin
} from '../api/inventory';
import {
   validateFloatValue,
   validatePurchasePrice,
   validateSkinName 
} from '../utils/validation';

export default function addSkinForm() {
    const [skinName, setSkinName] = useState('');
    const [floatValue, setFloatValue] = useState('');
    const [purchasePrice, setPurchasePrice] = useState('');
    const [validationError, setValidationError] = useState<string | null>(null);

    function handleSubmit() {
        const trimmedName = skinName.trim();
        let nameError = validateSkinName(trimmedName);
        let floatError = validateFloatValue(floatValue);
        let priceError = validatePurchasePrice(purchasePrice);
        const error = nameError ?? floatError ?? priceError;
        setValidationError(error);
        
        if (error != null) {
            return
        }

        const skin: NewSkin = {
            skin_name: trimmedName,
            float_val: parseFloat(floatValue),
            purchase_price: parseFloat(purchasePrice)
        };

        addSkin(skin);
    }


    return (
        <>
            <p>Skin Name</p>
            <input value={skinName} onChange={(event) => setSkinName(event.target.value)}/>
            <p>Float Value</p>
            <input value={floatValue} onChange={(event) => setFloatValue(event.target.value)}/>
            <p>Purchase Price</p>
            <input value={purchasePrice} onChange={(event) => setPurchasePrice(event.target.value)}/>
            <button onClick={handleSubmit}>Add {skinName} at {floatValue} purchased at {purchasePrice}</button>
            <p>{validationError}</p>
        </>
    );
}