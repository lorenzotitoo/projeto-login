const EM_DESENVOLVIMENTO = ["127.0.0.1", "localhost"].includes(window.location.hostname);
 
const API_URL = EM_DESENVOLVIMENTO
    ? "http://127.0.0.1:5000"
    : "https://SEU-SERVICO.onrender.com";