import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from './assets/vite.svg'
import heroImg from './assets/hero.png'
import './App.css'
import AddSkinForm from './components/AddSkinsForm'

function App() {
  const [count, setCount] = useState(0)

  return (
    <>
      <section id="center">
        <AddSkinForm />
      </section>
    </>
  )
}

export default App
