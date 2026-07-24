import { useEffect, useState } from 'react'
import {
    getInventory, type Skin
} from '../api/inventory'

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
                <p>{skin.skin_name}</p>
            ))}
        </>
    );
}