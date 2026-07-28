import { useState } from 'react';
import {
    addSkin, type NewSkin
} from '../api/inventory';
import {
   validateFloatValue,
   validatePurchasePrice,
   validateSkinName 
} from '../utils/validation';

interface AddSkinFormProps {
    onSkinAdded: () => Promise<void>;
}

export default function addSkinForm({ onSkinAdded }: AddSkinFormProps) {
    const [skinName, setSkinName] = useState('');
    const [floatValue, setFloatValue] = useState('');
    const [purchasePrice, setPurchasePrice] = useState('');
    const [validationError, setValidationError] = useState<string | null>(null);
    const [stateText, setStateText] = useState('');

    async function handleSubmit() {
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

        const addState = await addSkin(skin); 
        if (addState.status == 'added') {
            setStateText(`Added ${trimmedName} to the inventory successfully`);
            onSkinAdded();
        }
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
            <p>{stateText}</p>
        </>
    );
}