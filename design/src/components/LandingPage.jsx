import React, { useState } from 'react';
import '../styles/landingStyles.scss';
import logo from '../images/alGOLD2.png';
import { validateID, validateToken, validateType, checkEmptyFields } from '../utils/ValidateInputs';

const LandingPage = () => {
  const [id, setID] = useState('');
  const [token, setToken] = useState('');
  const [type, setType] = useState('');

  const [errors, setErrors] = useState({
    idError: '',
    tokenError: '',
    typeError: '',
  });

  const handleSubmit = async () => {
    let validationErrors = {
      idError: '',
      tokenError: '',
      typeError: '',
    };

    if (checkEmptyFields([id, token, type])) {
      if (!id) validationErrors.idError = 'ID cannot be empty';
      if (!token) validationErrors.tokenError = 'Token cannot be empty';
      if (!type) validationErrors.typeError = 'Type cannot be empty';
    } else {
      if (!validateID(id)) {
        validationErrors.idError = 'INVALID ID';
      }

      if (!validateToken(token)) {
        validationErrors.tokenError = 'INVALID TOKEN';
      }

      if (!validateType(type)) {
        validationErrors.typeError = 'INVALID TYPE';
      }
    }

    setErrors(validationErrors);

    if (!validationErrors.idError && !validationErrors.tokenError && !validationErrors.typeError) {
      try {
        const response = await fetch('http://127.0.0.1:3000/submit', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ id, token, type }),
        });

        const data = await response.json();

        if (data.message === 'Success') {
          console.log('Historical Data: ', data.historical_data);
          alert('Historical data retrieved.');
        } else {
          alert('Error: ' + data.message);
        }
      } catch (error) {
        alert('Failed to connect to the server.');
      }
    }
  };

  return (
    <div className="landingContainer">
      <div className="landingBox">
        <img src={logo} alt="Logo" className="landingLogo" />
        <div className="inputContainer">
          <input
            type="text"
            className="landingInput"
            placeholder="ACCOUNT ID"
            id="accountID"
            value={id}
            onChange={(e) => setID(e.target.value)}
          />
          <p className="error">{errors.idError}</p>
          <input
            type="text"
            className="landingInput"
            placeholder="ACCESS TOKEN"
            id="accessToken"
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
          <p className="error">{errors.tokenError}</p>
          <input
            type="text"
            className="landingInput"
            placeholder="ACCOUNT TYPE"
            id="accountType"
            value={type}
            onChange={(e) => setType(e.target.value)}
          />
          <p className="error">{errors.typeError}</p>
          <button className="launchBTN" onClick={handleSubmit}>
            LAUNCH
          </button>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
