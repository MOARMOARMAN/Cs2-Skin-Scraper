import {
    type Skin
} from '../api/inventory';

interface AddInventoryDisplayProps {
    inventorySkins: Skin[];
}

export default function addInventoryDisplay({inventorySkins}: AddInventoryDisplayProps) {
    const today = new Date();

    return (
        <>
            {inventorySkins.map((skin: Skin) => {
                const recordedDate = new Date(skin.recorded_at);
                // Calculate difference in days
                const daysPassed = (today.getTime() - recordedDate.getTime()) / (1000 * 3600 * 24);
                const isReady = daysPassed >= 7;

                // Apply a light green or light red background depending on readiness
                const rowStyle = {
                    backgroundColor: isReady ? 'rgba(144, 238, 144, 0.4)' : 'rgba(255, 99, 71, 0.4)',
                    padding: '8px',
                    margin: '4px 0',
                    borderRadius: '4px'
                };

                return (
                    <p key={skin.id_} style={rowStyle}>
                        {skin.id_} | {skin.skin_name} | {skin.float_val} | {skin.purchase_price} | {skin.recorded_at} | {skin.expected_sale_price} | {skin.profit}
                    </p>
                );
            })}
        </>
    );
}