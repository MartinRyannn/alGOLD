import React, { useEffect, useState } from 'react';

const ScreenSizeProtection = () => {
  const [showOverlay, setShowOverlay] = useState(false);
  const [currentWidth, setCurrentWidth] = useState(window.innerWidth);
  
  const checkScreenSize = () => {
    const width = window.innerWidth;
    setCurrentWidth(width);
    setShowOverlay(width < 1200);
  };
  
  useEffect(() => {
    checkScreenSize();
    window.addEventListener('resize', checkScreenSize);
    
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'childList') {
          const overlayElement = document.getElementById('protected-overlay');
          if (!overlayElement || overlayElement.style.display === 'none') {
            checkScreenSize();
          }
        }
      });
    });
    
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true
    });
    
    const handleContextMenu = (e) => {
      if (window.innerWidth < 1200) {
        e.preventDefault();
      }
    };
    
    document.addEventListener('contextmenu', handleContextMenu);
    
    return () => {
      window.removeEventListener('resize', checkScreenSize);
      document.removeEventListener('contextmenu', handleContextMenu);
      observer.disconnect();
    };
  }, []);
  
  if (!showOverlay) return null;
  
  return (
    <>
      <div
        id="protected-overlay"
        className="protected-overlay"
      >
        <div className="content-wrapper">
          <div className="circles-background">
            <div className="circle circle-small" />
            <div className="circle circle-medium" />
            <div className="circle circle-large" />
          </div>
          
          <div className="screen-size-indicator">
            Current width: {currentWidth}px
          </div>

          <h1 className="title">
            Screen Size Not Supported
          </h1>
          
          <div className="info-container">
            <p className="description">
              This application requires a minimum screen width of{' '}
              <span className="highlight">1200px</span> for optimal viewing.
              Please use a larger device or resize your browser window.
            </p>
            
            <div className="progress-bar-container">
              <div 
                className="progress-bar"
                style={{ width: `${Math.min((currentWidth / 1200) * 100, 100)}%` }}
              />
            </div>
            
            <div className="required-width">
              Required: 1200px
            </div>
          </div>
        </div>
      </div>
      <style>{`
        :root {
          --white: #E5F0E9;
          --black: #050A06;
          --lgreen: #9DDBB3;
          --mgreen: #268246;
          --green: #52D981;
          --greent: #52d9817d;
        }

        .protected-overlay {
          position: fixed !important;
          inset: 0;
          width: 100vw !important;
          height: 100vh !important;
          background-color: var(--black) !important;
          z-index: 9999;
          display: flex !important;
          align-items: center;
          justify-content: center;
          text-align: center;
          padding: 1.5rem;
          user-select: none;
          pointer-events: auto;
          touch-action: none;
        }

        .content-wrapper {
          position: relative;
          display: flex;
          flex-direction: column;
          align-items: center;
          animation: fadeIn 0.5s ease-out forwards;
        }

        .circles-background {
          position: absolute;
          inset: 0;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .circle {
          position: absolute;
          border-radius: 50%;
        }

        .circle-small {
          width: 8rem;
          height: 8rem;
          background-color: rgba(157, 219, 179, 0.2);
          animation: pulse-slow 3s infinite;
        }

        .circle-medium {
          width: 12rem;
          height: 12rem;
          background-color: rgba(157, 219, 179, 0.1);
          animation: pulse-slower 4s infinite;
        }

        .circle-large {
          width: 16rem;
          height: 16rem;
          background-color: rgba(157, 219, 179, 0.05);
          animation: pulse-slowest 5s infinite;
        }

        .screen-size-indicator {
          color: var(--lgreen);
          margin-bottom: 1rem;
          font-family: monospace;
          animation: slideDown 0.5s ease-out forwards;
          animation-delay: 0.2s;
          opacity: 0;
        }

        .title {
          font-size: 2.5rem;
          font-weight: bold;
          margin-bottom: 1.5rem;
          background: linear-gradient(to right, var(--lgreen), var(--green));
          -webkit-background-clip: text;
          background-clip: text;
          color: transparent;
          animation: slideIn 0.5s ease-out forwards;
        }

        .info-container {
          position: relative;
          max-width: 28rem;
        }

        .description {
          font-size: 1.125rem;
          color: var(--white);
          line-height: 1.75;
          margin-bottom: 2rem;
          animation: fadeIn 0.5s ease-out forwards;
          animation-delay: 0.4s;
          opacity: 0;
        }

        .highlight {
          color: var(--lgreen);
          font-weight: bold;
        }

        .progress-bar-container {
          width: 16rem;
          height: 0.5rem;
          background-color: var(--black);
          border: 1px solid var(--mgreen);
          border-radius: 9999px;
          overflow: hidden;
          margin-bottom: 1rem;
        }

        .progress-bar {
          height: 100%;
          background-color: var(--green);
          transition: width 0.3s ease;
          border-radius: 9999px;
        }

        .required-width {
          font-size: 0.875rem;
          color: var(--white);
          animation: pulse 2s infinite;
        }

        @keyframes pulse-slow {
          0%, 100% { transform: scale(1); opacity: 0.2; }
          50% { transform: scale(1.1); opacity: 0.3; }
        }
        
        @keyframes pulse-slower {
          0%, 100% { transform: scale(1); opacity: 0.1; }
          50% { transform: scale(1.15); opacity: 0.2; }
        }
        
        @keyframes pulse-slowest {
          0%, 100% { transform: scale(1); opacity: 0.05; }
          50% { transform: scale(1.2); opacity: 0.1; }
        }
        
        @keyframes slideIn {
          from { transform: translateY(-20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        
        @keyframes slideDown {
          from { transform: translateY(-40px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        @keyframes pulse {
          0%, 100% { opacity: 0.7; }
          50% { opacity: 1; }
        }

        @media (min-width: 1200px) {
          #protected-overlay {
            display: none !important;
          }
        }
      `}</style>
    </>
  );
};

export default ScreenSizeProtection;
