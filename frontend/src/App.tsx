import { useEffect, useState } from 'react'
import './App.css'
import AddSkinForm from './components/AddSkinsForm'
import AddInventoryDisplay from './components/AddInventoryDisplay'
import AddRemoveSkinForm from './components/RemoveSkinsForm'
import {
  type Skin, getInventory
} from './api/inventory'

function App() {
  const [inventorySkins, setInventorySkins] = useState<Skin[]>([]);

  async function refreshInventory() {
    const skins = await getInventory();
    setInventorySkins(skins);
  }

  useEffect(() => {
    refreshInventory();
  }, []);

  return (
    <>
      <section id="center">
        <AddSkinForm onSkinAdded={refreshInventory} />
        <AddInventoryDisplay inventorySkins={inventorySkins} />
        <AddRemoveSkinForm onSkinRemoved={refreshInventory} />
      </section>
    </>
  )
}

export default App
