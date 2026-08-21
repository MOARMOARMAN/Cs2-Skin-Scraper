import { useState } from "react";
import {
   delSkin 
} from '../api/inventory'

interface RemoveSkinsFormProps {
    updateSkinList: () => Promise<void>;
    updateBalance: () => Promise<void>;
}

export default function RemoveSkinsForm({ updateSkinList, updateBalance }: RemoveSkinsFormProps) {
    const [removeID, setRemoveID] = useState('');
    const [stateText, setStateText] = useState('');

    async function handleSubmit() {
        const toRemoveID = parseFloat(removeID);
        const deleteState = await delSkin(toRemoveID);
        if (deleteState.status == "deleted") {
            setStateText(`Successfully deleted ${toRemoveID} from inventory`);
            updateSkinList();
            updateBalance();
        } else if (deleteState.status == "not deleted") {
            setStateText(`Failed to delete ${toRemoveID} from inventory. Likely Invalid ID.`)
        }
    }

    return (
        <>
            <input value={removeID} onChange={(event) => setRemoveID(event.target.value)}></input>
            <button onClick={handleSubmit}>Delete the inventory skin with ID {removeID}</button>
            <p>{stateText}</p>
        </>
    );
}
