import React from 'react';
import axios from 'axios'; // Make sure to install axios if you haven't already
import '../styles/toolsStyles.scss';

const Tools = ({ showTools, setShowTools }) => {
  
  // Function to handle the "PRACTICE TRADING" button click
  const handlePracticeTradingClick = async () => {
    try {
      const response = await axios.post('http://localhost:3001/launch-trading-app');
      console.log("Response from server:", response.data.message); // Handle success response
    } catch (error) {
      console.error("Error launching trading app:", error.response ? error.response.data : error.message);
    }
  };
  const handleHistoryTradingClick = async () => {
    try {
      const response = await axios.post('http://localhost:3001/launch-history-app');
      console.log("Response from server:", response.data.message); // Handle success response
    } catch (error) {
      console.error("Error launching trading app:", error.response ? error.response.data : error.message);
    }
  };

  return (
    <div className={`toolsContainer ${showTools ? 'show' : 'hide'}`}>
      <div className="toolsTop">
        <button className="closeButton" onClick={() => setShowTools(false)}>
        </button>
      </div>
      <button className="toolBox" onClick={handlePracticeTradingClick}>
        <div className="toolTitle">PRACTICE TRADING</div>
      </button>
      <button className="toolBox" onClick={handleHistoryTradingClick}>
        <div className="toolTitle">HISTORICAL DATA</div>
      </button>
      <button className="toolBox">
        <div className="toolTitle">TRADE PANNEL</div>
      </button>
      <button className="toolBox">
        <div className="toolTitle">COMING SOON</div>
      </button>
      <button className="toolBox">
        <div className="toolTitle">COMING SOON</div>
      </button>
      
      
    </div>
  );
};

export default Tools;
