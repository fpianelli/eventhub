import { setupCommentDeletion } from './comments.js'; 
import { setupEventCountdown } from './event_countdown.js';

document.addEventListener('DOMContentLoaded', function() {
    //Configurar la eliminación de comentarios
    setupCommentDeletion();
    
    //Configurar el contador del evento
    const countdownInterval = setupEventCountdown();
    
    //Limpiar el intervalo cuando la página se descargue
    window.addEventListener('beforeunload', function() {
        if (countdownInterval) {
            clearInterval(countdownInterval);
        }
    });
});