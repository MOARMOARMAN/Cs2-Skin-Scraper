import { useEffect, useState } from 'react';
import {
    getInventory, type Skin
} from '../api/inventory';

export default function addInventoryDisplay() {
    const [inventorySkins, setInventorySkins] = useState<Skin[]>([]);

    useEffect(
        () => {
            async function loadInventory() {
                const skins = await getInventory();
                setInventorySkins(skins);
            }

            loadInventory();
        },
        []
    );

    return (
        <>
            {inventorySkins.map((skin: Skin) => (
                <p>{skin.id_} | {skin.skin_name} | {skin.float_val} | {skin.purchase_price} | {skin.recorded_at}</p>
                
            ))}
        </>
    );
}