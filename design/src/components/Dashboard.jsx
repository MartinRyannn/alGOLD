import React, { useState, useEffect } from 'react';
import '../styles/dashboardStyles.scss';
import logo from '../images/alGOLD2.png';
import Calendar from './Calendar';
import ScreenSizeProtection from '../extras/ScreenSizeProtection.jsx';
import { Line } from 'react-chartjs-2';
import moment from 'moment';
import Tools from '../extras/Tools.jsx';
import 'chartjs-adapter-date-fns';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
} from 'chart.js';
import 'chartjs-plugin-annotation';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
);

const MAX_CANDLES = 30;


const Dashboard = () => {
  const [volatility, setVolatility] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [tVwap, setTVwap] = useState(null);
  const [statusOn, setStatusOn] = useState(false);
  const [loading, setLoading] = useState(false);
  const [unrealizedPL, setUnrealizedPL] = useState(0);
  const [todaysPL, setTodaysPL] = useState(0);
  const [profitLoss, setProfitLoss] = useState(0);
  const [currentSession, setCurrentSession] = useState('');
  const sessions = [
    { name: 'LONDON', start: 7, end: 15 },
    { name: 'NEW YORK', start: 15, end: 24 },
    { name: 'TOKYO', start: 3, end: 7 },
  ];
  const [chartData, setChartData] = useState({
    labels: [],
    datasets: [
      {
        label: 'Close Price',
        data: [],
        fill: false,
        backgroundColor: 'rgba(75,192,192,0.2)',
        borderColor: 'rgba(75,192,192,1)',
      },
    ],
  });
  const [balance, setBalance] = useState(null);
  const [consoleLogs, setConsoleLogs] = useState([]);
  const [lastTimestamp, setLastTimestamp] = useState(null);
  const [rsiValue, setRsiValue] = useState(null);
  const [showTools, setShowTools] = useState(false);
  const [activeTrades, setActiveTrades] = useState([]);
  const [latestPrice, setLatestPrice] = useState(null);
  const [livePrice, setLivePrice] = useState(null);
  const [tradeHistory, setTradeHistory] = useState([]);
  const [realTimeChartData, setRealTimeChartData] = useState({
    labels: [],
    datasets: [
      {
        label: 'Real-Time Price',
        data: [],
        fill: false,
        backgroundColor: 'rgba(0, 255, 0, 0.15)',
        borderColor: 'rgba(0, 255, 0, 0.6)',
        pointRadius: 0,
      },
    ],
  });

  const [pivotPoints, setPivotPoints] = useState([]);

  const transactions = [
    { price: '2431.45', pl: '+150', pips: '0.02' },
    { price: '2432.30', pl: '-50', pips: '0.02' },
    { price: '2431.90', pl: '+75', pips: '0.02' },
    { price: '2432.30', pl: '-50', pips: '0.02' },
    { price: '2431.90', pl: '+75', pips: '0.02' },
  ];
  const addLog = (message, type) => {
    const newLog = { message, type };
    setConsoleLogs((prevLogs) => [...prevLogs, newLog]);
  };




  const chartOptions = {
    responsive: true,
    plugins: {
      legend: { display: true },
      annotation: {
        annotations: {
          
        },
      },
    },
    scales: {
      x: {
        type: 'time',
        time: { unit: 'minute' },
        display: true,
      },
      y: { display: true },
    },
  };
  

  const updateCurrentSession = () => {
    const now = new Date();
    const latviaOffset = now.getTimezoneOffset() * 60 * 1000; 
    const localTime = new Date(now.getTime() + latviaOffset + (3 * 60 * 60 * 1000)); 

    const currentHour = localTime.getUTCHours();

    let activeSession = 'CLOSED';
    for (const session of sessions) {
      const adjustedStart = session.start >= 24 ? session.start - 24 : session.start;
      const adjustedEnd = session.end >= 24 ? session.end - 24 : session.end;

      if (
        (adjustedStart < adjustedEnd && currentHour >= adjustedStart && currentHour < adjustedEnd) ||
        (adjustedStart > adjustedEnd && (currentHour >= adjustedStart || currentHour < adjustedEnd))
      ) {
        activeSession = session.name;
        break;
      }
    }
    setCurrentSession(activeSession);
  };

  const formatDate = (date) => {
    const options = { year: 'numeric', month: 'numeric', day: 'numeric' };
    return new Intl.DateTimeFormat('en-US', options).format(date);
  };


    const fetchActiveTrades = async () => {
      try {
        const response = await fetch('http://localhost:3001/get_active_trades');
        const result = await response.json();

        if (result.status === 'Success') {
          setActiveTrades(result.data);
          calculateTodaysPL(result.data);
        } else {
          console.error(result.status);
        }
      } catch (error) {
        console.error('Error fetching active trades:', error);
      }
    };

    const calculateTodaysPL = (trades) => {
      const today = moment().startOf('day');
      let plSum = 0;
  
      trades.forEach(trade => {
        const tradeOpenTime = moment(trade.openTime);

        if (tradeOpenTime.isSame(today, 'day')) {
          plSum += parseFloat(trade.unrealizedPL);
        }
      });
  
      setTodaysPL(plSum.toFixed(2));
    };

  
  useEffect(() => {
    const sessionInterval = setInterval(updateCurrentSession, 10000);
    updateCurrentSession();

    return () => {
      clearInterval(sessionInterval);
    };
  }, []);

  useEffect(() => {
    let dataInterval, balanceInterval, livePriceInterval;

    const fetchData = async () => {
  try {
    setLoading(true);

    const [response] = await Promise.all([
      fetch('http://localhost:3001/get_data'),
    ]);

    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    const data = await response.json();
    console.log('Fetched Data:', data);

    if (data.length > 0) {
      const newLabels = [];
      const newCloseData = [];

      const latestData = data[data.length - 1];
      setRsiValue(latestData.RSI);
      setLatestPrice(latestData.Close);

      data.forEach((entry) => {
        const date = new Date(entry.Time);
        newLabels.push(date);
        newCloseData.push({ x: date, y: entry.Close });

        if (!lastTimestamp || date > lastTimestamp) {
          setConsoleLogs((prevLogs) => [
            ...prevLogs,
            `New Candle: Close Price - ${entry.Close}`,
          ]);
          setLastTimestamp(date);
        }
      });

      const limitedLabels = newLabels.slice(-MAX_CANDLES);
      const limitedCloseData = newCloseData.slice(-MAX_CANDLES);

      setChartData({
        labels: limitedLabels,
        datasets: [
          {
            label: 'Close Price',
            data: limitedCloseData,
            fill: false,
            backgroundColor: 'rgba(75,192,192,0.2)',
            borderColor: 'rgba(75,192,192,1)',
          },
        ],
      });
    }

    setLoading(false);
  } catch (error) {
    addLog(`Error fetching chart data: ${error.message}`, 'error');
  } finally {
    setLoading(false);
  }
};


    const fetchBalance = async () => {
      try {
        const response = await fetch('http://localhost:3001/get_balance');

        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Fetched Balance:', data);
        setBalance(data.balance);
      } catch (err) {
        console.error('Error fetching balance:', err);
      }
    };

    const fetchUnrealizedPL = async () => {
      try {
        const response = await fetch('http://localhost:3001/get_unrealised');
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const data = await response.json();
        console.log('Fetched Unrealized PL:', data);
        setUnrealizedPL(data.unrealizedPL);
      } catch (err) {
        console.error('Error fetching unrealized PL:', err);
      }
    };
    
    const fetchProfitLoss = async () => {
      try {
        const response = await fetch('http://localhost:3001/get_profit');
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const data = await response.json();
        console.log('Fetched Profit/Loss:', data);
        setProfitLoss(data.pl);
      } catch (err) {
        console.error('Error fetching profit/loss:', err);
      }
    };
    const fetchTradeHistory = async () => {
      try {
          const response = await fetch('http://localhost:3001/get_history');
          if (!response.ok) {
              throw new Error(`HTTP error! Status: ${response.status}`);
          }
          const data = await response.json();
          console.log('Fetched Trade History:', data);
          setTradeHistory(Array.isArray(data.data) ? data.data : []);
      } catch (err) {
          console.error('Error fetching trade history:', err);
      }
  };
  
    
    

    const fetchLivePrice = async () => {
      try {
        const response = await fetch('http://localhost:3001/get_live_price');
    
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
    
        const data = await response.json();
        setLivePrice(data.live_price);

        const currentTime = new Date();
        setRealTimeChartData(prevData => {
          const updatedData = {
            labels: [...prevData.labels, currentTime],
            datasets: [
              {
                ...prevData.datasets[0],
                data: [...prevData.datasets[0].data, { x: currentTime, y: data.live_price }]
              },
            ],
          };
    
          if (updatedData.labels.length > 50) {
            updatedData.labels = updatedData.labels.slice(-30);
            updatedData.datasets[0].data = updatedData.datasets[0].data.slice(-30);
          }
    
          return updatedData;
        });
      } catch (err) {
        console.error('Error fetching live price:', err);
      }
    };
    
    
    

    const fetchPivotPoints = async () => {
      try {
        const response = await fetch('http://localhost:3001/get_pivots');
    
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
    
        const data = await response.json();
        console.log('Fetched Pivot Points:', data);
    
        setPivotPoints({
          pivot_point: data.pivot_point,
          r1: data.r1,
          r2: data.r2,
          s1: data.s1,
          s2: data.s2,
        });
      } catch (err) {
        console.error('Error fetching pivot points:', err);
      }
    };
    

    const fetchVolatility = async () => {
      try {
        const response = await fetch('http://localhost:3001/get_volatility');
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
    
        const data = await response.json();
        console.log('Fetched Volatility:', data);
        
        // Set the fetched values to state
        setVolatility(data.volatility);       // Set volatility
        setTVwap(data.t_vwap);                // Set T-VWAP
        setLastUpdated(data.last_updated);     // Update lastUpdated timestamp
    
      } catch (err) {
        console.error('Error fetching volatility:', err);
      }
    };
    
    

    if (statusOn) {
      fetchData();
      fetchPivotPoints();
      fetchTradeHistory();
      fetchActiveTrades();
      fetchVolatility();
  
      dataInterval = setInterval(fetchData, 5000);
      volatilityInterval = setInterval(fetchVolatility, 2000);
      historyInterval = setInterval(fetchTradeHistory, 5000);
      activeInterval = setInterval(fetchActiveTrades, 2000);
      balanceInterval = setInterval(() => {
        fetchBalance();
        fetchUnrealizedPL();
        fetchProfitLoss();
      }, 2000);

      fetchLivePrice();
      livePriceInterval = setInterval(fetchLivePrice, 1000);
    } else {
      setChartData({
        labels: [],
        datasets: [{ label: 'Close Price', data: [], fill: false, backgroundColor: 'rgba(75,192,192,0.2)', borderColor: 'rgba(75,192,192,1)' }],
      });
      setRealTimeChartData({
        labels: [],
        datasets: [{ label: 'Close Price', data: [], fill: false, backgroundColor: 'rgba(0, 255, 0, 0.15)',
          borderColor: 'rgba(0, 255, 0, 0.6)',
          pointRadius: 0, }],
      });
      
      setUnrealizedPL(0);
      setLivePrice(0); 
      setProfitLoss(0);
      setBalance(null);
      setConsoleLogs([]);
      setTradeHistory([]);
      setVolatility(0);
      setActiveTrades([]);
      setPivotPoints([]);
      setLastTimestamp(null); 
    }
  
    return () => {
      clearInterval(dataInterval);
      clearInterval(balanceInterval);
      clearInterval(historyInterval);
      clearInterval(volatilityInterval);
      clearInterval(livePriceInterval);
      clearInterval(activeInterval);
    };
  }, [statusOn]);
  
    const handleToggleStatus = () => {
    setStatusOn((prev) => !prev);
    addLog(`Data retrieval ${statusOn ? 'stopped' : 'started'}`, 'info');
  };
  
  let dataInterval, balanceInterval, historyInterval, activeInterval, volatilityInterval;
  

  const toggleStatus = () => {
    setStatusOn((prevStatus) => !prevStatus); // Toggle the status

    // Check if events array is not empty before logging
    // if (events.length > 0) {
    //     // Safely access the first event
    //     const { due, impact, forecast } = events[0]; // Destructure values for clarity
    //     console.log('Due:', due || 'N/A'); // Log 'N/A' if due is undefined or null
    //     console.log('Impact:', impact || 'N/A'); // Log 'N/A' if impact is undefined or null
    //     console.log('Forecast:', forecast || 'N/A'); // Log 'N/A' if forecast is undefined or null
    // } else {
    //     console.log('No upcoming events to log.');
    // }
};



const getColorByType = (type) => {
  switch (type) {
    case 'error':
      return 'red';
    case 'server':
      return 'lightblue';
    default:
      return 'white';
  }
};
const handleToggleTools = () => {
  setShowTools(prev => !prev);
};

  return (
    <div className="dashboardContainer">
      <ScreenSizeProtection />
      <Tools showTools={showTools} setShowTools={setShowTools} />
      <div className="dashHeader">
        <img src={logo} alt="Logo" className="dashLogo" />
        <button 
          className={`statusButton ${statusOn ? 'On' : 'Off'}`} 
          onClick={handleToggleStatus}
        >

        </button>
        <button className="toolsButton" onClick={handleToggleTools}>
          TOOLS
        </button>

      </div>

      <div className="boxContainer">
        <div className="dashBox L">
          <div className="chartBox">
            <div className="chartTop">
              <div
                className="chartDataBox"
                style={{
                  color: rsiValue > 75 ? 'red' : rsiValue <= 25 ? 'green' : 'white',
                }}
              >
                {typeof rsiValue === 'number' ? rsiValue.toFixed(2) : 'N/A'}
              </div>
              <div className="chartDataBox Long">
                <div className="datalong">
                  {latestPrice !== null ? latestPrice.toFixed(2) : '...'}
                </div>
              </div>
              <div className="chartDataBox">XAU_USD</div>
            </div>
            <div className="chart">
              <Line data={chartData} options={chartOptions} />
            </div>
          </div>
          <div className="rightContainer">
          <div className="eventsBox">
  <div className="eventTitle">CURRENT VOLATILITY</div>
  {volatility === null ? (
    <div className="loading">Calculating...</div>
  ) : (
    <div>
      <div className="volatilityValue">
  {volatility && volatility > 0 ? `Volatility: ${volatility.toFixed(4)}` : "Getting Data..."}
</div>

      <div className="volatilityProgress">
        <div
          className="volatilityBar"
          style={{
            width: `${(volatility / 1) * 100}%`, // Scale the width based on max of 0.5
            backgroundColor: `rgba(255, 0, 0, ${Math.min(volatility / 0.5, 4)})`, // Color based on value
          }}
        />
      </div>
      <div className="volatilityLabels">
        <span className="label left-label">0</span>
        <span className="label right-label">1</span>
      </div>

      <div className="eventTitle">CURRENT T-VWAP</div>
      <div className="tVwapValue">{`${tVwap !== null ? tVwap.toFixed(4) : 'N/A'}`}</div>
    </div>
  )}
</div>



              <div className="sessionBox">
              <div className="eventTitle">CURRENT SESSION</div>
              <div className="currentSession">
                <div className="sessionTitle">{currentSession}</div>
                <div className="sessionTimes">
                  {currentSession === 'LONDON' && '07:00 - 15:00'}
                  {currentSession === 'NEW YORK' && '15:00 - 00:00'}
                  {currentSession === 'TOKYO' && '03:00 - 07:00'}
                  {currentSession === 'CLOSED' && 'CLOSED'}
                </div>
              </div>
              <div className="nextSession">{currentSession === 'LONDON' ? 'NEW YORK' : currentSession === 'NEW YORK' ? 'TOKYO' : 'LONDON'}</div>
            </div>
          </div>
          
        </div>

        <div className="dashBox S">
        <div className="activeTradesBox">
      <div className="activeHeading">ACTIVE TRADES</div>
      
      {activeTrades.length > 0 ? (
        activeTrades.map((trade, index) => (
          <div className="activeBox" key={index}>
            <div className="activeDir">
              {trade.currentUnits > 0 ? 'LONG' : 'SHORT'}
            </div>
            <div className="activePL" style={{ color: trade.unrealizedPL > 0 ? 'green' : 'red' }}>
              {trade.unrealizedPL}
            </div>
            
            <div className="activeUnits">{trade.currentUnits}</div>
          </div>
        ))
      ) : (
        <div className='noEvent'>No active trades available.</div>
      )}
    </div>
          <div className="logBox algo">
            <div className="logBoxTitle">PIVOT POINTS</div>
            <div className="pivotPointsList">
              {Object.keys(pivotPoints).length > 0 ? (
                <>
                  <div className="pivotPoint">
                    <span>Pivot Point:</span> <span>{pivotPoints.pivot_point?.toFixed(2) || 'N/A'}</span>
                  </div>
                  <div className="pivotPoint">
                    <span>Resistance 1 (R1):</span> <span>{pivotPoints.r1?.toFixed(2) || 'N/A'}</span>
                  </div>
                  <div className="pivotPoint">
                    <span>Resistance 2 (R2):</span> <span>{pivotPoints.r2?.toFixed(2) || 'N/A'}</span>
                  </div>
                  <div className="pivotPoint">
                    <span>Support 1 (S1):</span> <span>{pivotPoints.s1?.toFixed(2) || 'N/A'}</span>
                  </div>
                  <div className="pivotPoint">
                    <span>Support 2 (S2):</span> <span>{pivotPoints.s2?.toFixed(2) || 'N/A'}</span>
                  </div>
                </>
              ) : (
                <div className='noEvent'>No pivot points available.</div>
              )}
            </div>
          </div>
        </div>

        <div className="dashBox XS">
  <div className="historyHeading">TRADE HISTORY</div>
  {tradeHistory.length > 0 ? (
    tradeHistory.slice().reverse().map((trade, index) => (
      <div className="historyBox" key={index}>
        <div className="historyUnits">{trade.units}</div> 
        <div className="historyPL" style={{ color: trade.pl > 0 ? 'green' : 'red' }}>
          {trade.pl} 
        </div>
        <div className="historyPrice">{trade.price}</div>
      </div>
    ))
  ) : (
    <div className='noEvent'>No trade history available.</div>
  )}
</div>


        <div className="dashBox Mn">
          <div className="balanceBox">
            <div className="balanceHeading">CURRENT BALANCE: </div>
            <div className="balance">
              {balance !== null ? `${balance} USD` : '...'}
            </div>
            <div className="balanceBottomLeft">
             
            </div>
            <div className="balanceBottomRight">
              <button className="transactionsButton">PRACTICE</button>
            </div>
          </div>
          <div className="infoBox">
            <div className="balanceHeading low">STATS: </div>
            <div className="statBox">
  <div className={`statCount ${unrealizedPL < 0 ? 'redText' : 'greenText'}`}>
    {unrealizedPL.toFixed(2)}
  </div>
  <div className="statTitle">UNREALISED PROFIT</div>
</div>

<div className="statBox">
  <div className={`statCount ${profitLoss < 0 ? 'redText' : 'greenText'}`}>
    {profitLoss.toFixed(2)}
  </div>
  <div className="statTitle">PROFIT/LOSS</div>
</div>

          </div>
        </div>

        <div className="dashBox M">
          <div className="realTimeChartBox">
            <div className="realTimeChartTitle">
              {livePrice !== null ? livePrice.toFixed(2) : '...'}
            </div>
            <Line className="chartLive" data={realTimeChartData} options={chartOptions} />
          </div>
        </div>
      </div>
    </div>
  );
};



export default Dashboard;
