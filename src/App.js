import Navbar from './components/Navbar'; 
import Alert from './components/Alert';
import TextForm from './components/TextForm';
import About from './components/About';
import { useState } from 'react';
import './App.css';
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Link
} from "react-router-dom";

function App() {
  const [mode, setMode] = useState('light'); // Mode state to track light/dark mode
  const [alert, setAlert] = useState(null);

  const showAlert = (message, type) => {
    setAlert({
      msg: message,
      type: type,
    });
    setTimeout(() => {
      setAlert(null);
    }, 1500);
  };

  // Toggle function to switch between light and dark mode
  const toggleSwitch = () => {
    if (mode === 'light') {
      setMode('dark'); // Change mode to dark
      document.body.style.backgroundColor = '#042743'; // Setting dark mode background color
      showAlert('Dark mode enabled', 'success');
    } else {
      setMode('light'); // Change mode to light
      document.body.style.backgroundColor = 'white'; // Setting light mode background color
      showAlert('Light mode enabled', 'success');
    }
  };

  return (
    <>
      <Router>
        <Navbar
          title="TextUtils"
          about="About"
          mode={mode}
          toggleMode={toggleSwitch}
        />
        <Alert alert={alert} />
        <div className="container my-3">
          <Routes>
            <Route exact path="/about" element={<About />} />
            <Route exact  path="/" element={
              <TextForm
                heading="Enter the text to analyze below"
                mode={mode}
                alert={alert}
                showAlert={showAlert}
              />
            } />
          </Routes>
        </div>
      </Router>
    </>
  );
}

export default App;
