import { useEffect, useState } from 'react';
import {
    getInventory, type Skin
} from '../api/inventory';

interface AddInventoryDisplayProps {
    inventorySkins: Skin[];
}

export default function addInventoryDisplay({inventorySkins}: AddInventoryDisplayProps) {

    return (
        <>
            {inventorySkins.map((skin: Skin) => (
                <p>{skin.id_} | {skin.skin_name} | {skin.float_val} | {skin.purchase_price} | {skin.recorded_at}</p>
                
            ))}
        </>
    );
}