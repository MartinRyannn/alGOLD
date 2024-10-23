export const validateID = (id) =>{
    const idPattern = /^\d{3}-\d{3}-\d{8}-\d{3}$/;
    return idPattern.test(id)
}

export const validateToken = (token) => {
    const tokenPattern = /^[a-f0-9]{32}-[a-f0-9]{32}$/i;
    return tokenPattern.test(token);
  };
  
  export const validateType = (type) => {
    return type.toLowerCase() === 'live' || type.toLowerCase() === 'practice';
  };

  export const checkEmptyFields = (values) => {
    return values.some(value => value.trim() === "");
  };