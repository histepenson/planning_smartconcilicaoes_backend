const API_URL = import.meta.env.PROD 
  ? '' // Produção: path relativo
  : 'http://localhost:8000'; // Desenvolvimento: localhost

export { API_URL };