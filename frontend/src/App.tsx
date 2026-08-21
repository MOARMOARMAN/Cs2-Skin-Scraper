import { useEffect, useState } from 'react'
import './App.css'
import AddSkinForm from './components/AddSkinsForm'
import AddInventoryDisplay from './components/AddInventoryDisplay'
import AddRemoveSkinForm from './components/RemoveSkinsForm'
import DisplayBalanceInformation from './components/DisplayBalanceInformation'
import AddTransactionsForm from './components/AddTransactionsForm'
import {
  type Skin, getInventory, getBalance
} from './api/inventory'

function App() {
  const [inventorySkins, setInventorySkins] = useState<Skin[]>([]);
  const [currentBalance, setCurrentBalance] = useState<number>(0);

  async function refreshInventory() {
    const skins = await getInventory();
    setInventorySkins(skins);
  }

  async function refreshBalance() {
    const balance = await getBalance();
    setCurrentBalance(balance);
  }

  useEffect(() => {
    refreshInventory();
    refreshBalance();
  }, []);

  return (
    <>
      <section id="center">
        <AddSkinForm updateSkinList={refreshInventory} updateBalance={refreshBalance}/>
        <AddInventoryDisplay inventorySkins={inventorySkins} />
        <AddRemoveSkinForm updateSkinList={refreshInventory} updateBalance={refreshBalance} />
        <DisplayBalanceInformation currentBalance={currentBalance} />
        <AddTransactionsForm updateBalance={refreshBalance} />
      </section>
    </>
  )
}

export default App
