export function setupEventCountdown() {
    const countdownElement = document.getElementById('countdown-data');
    if (!countdownElement) {
        /*console.log("No hay contador en esta página");*/
        return null;
    }

    try {
        const countdownData = JSON.parse(countdownElement.textContent);
        const eventTime = new Date(countdownData.event_datetime);
        
        if (isNaN(eventTime.getTime())) {
            throw new Error("Fecha del evento inválida");
        }

        function updateDisplay(days, hours, minutes) {
            const updateElement = (selector, value) => {
                const el = document.querySelector(selector);
                if (el) el.textContent = value;
            };

            updateElement('.countdown-days', days);
            updateElement('.countdown-hours', hours);
            updateElement('.countdown-minutes', minutes);
        }

        function updateCountdown() {
            const now = new Date();
            const remainingMs = eventTime - now;
            
            if (remainingMs <= 0) {
                const container = document.querySelector('.countdown-container');
                if (container) {
                    container.innerHTML = `
                        <div class="alert alert-success text-center">
                            ¡El evento ha comenzado!
                        </div>
                    `;
                }
                clearInterval(interval);
                return;
            }
            
            const totalSeconds = Math.floor(remainingMs / 1000);
            updateDisplay(
                Math.floor(totalSeconds / (3600 * 24)),
                Math.floor((totalSeconds % (3600 * 24)) / 3600),
                Math.floor((totalSeconds % 3600) / 60)
            );
        }

        const interval = setInterval(updateCountdown, 60000);
        updateCountdown();

        return interval;
        
    } catch (error) {
        console.error("Error en el contador:", error);
        return null;
    }
}