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
  const [activeTab, setActiveTab] = useState<'inventory' | 'manage' | 'transactions'>('inventory');

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
    <div className="app-container">
      <header className="top-nav">
        <h1 className="logo">CS2 Tracker</h1>
        <nav className="tabs">
          <button 
            className={`tab-btn ${activeTab === 'inventory' ? 'active' : ''}`}
            onClick={() => setActiveTab('inventory')}
          >
            INVENTORY
          </button>
          <button 
            className={`tab-btn ${activeTab === 'manage' ? 'active' : ''}`}
            onClick={() => setActiveTab('manage')}
          >
            MANAGE SKINS
          </button>
          <button 
            className={`tab-btn ${activeTab === 'transactions' ? 'active' : ''}`}
            onClick={() => setActiveTab('transactions')}
          >
            TRANSACTIONS
          </button>
        </nav>
      </header>

      <main className="main-content">
        {activeTab === 'inventory' && (
          <div className="tab-pane">
            <DisplayBalanceInformation currentBalance={currentBalance} />
            <AddInventoryDisplay inventorySkins={inventorySkins} />
          </div>
        )}

        {activeTab === 'manage' && (
          <div className="tab-pane">
            <div className="forms-container">
              <div className="form-card">
                <h2>Add New Skin</h2>
                <AddSkinForm updateSkinList={refreshInventory} updateBalance={refreshBalance}/>
              </div>
              <div className="form-card">
                <h2>Remove Skin</h2>
                <AddRemoveSkinForm updateSkinList={refreshInventory} updateBalance={refreshBalance} />
              </div>
            </div>
          </div>
        )}

        {activeTab === 'transactions' && (
          <div className="tab-pane">
            <div className="form-card">
              <h2>Add Transaction</h2>
              <AddTransactionsForm updateBalance={refreshBalance} />
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
