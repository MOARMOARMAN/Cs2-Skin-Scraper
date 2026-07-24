import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from './assets/vite.svg'
import heroImg from './assets/hero.png'
import './App.css'
import AddSkinForm from './components/AddSkinsForm'
import AddInventoryDisplay from './components/AddInventoryDisplay'

function App() {
  const [count, setCount] = useState(0)

  return (
    <>
      <section id="center">
        <AddSkinForm />
        <AddInventoryDisplay />
      </section>
    </>
  )
}

export default App
